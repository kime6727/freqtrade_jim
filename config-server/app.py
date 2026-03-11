"""
FreqTrade 配置管理 API
提供配置读取、保存、验证和热重载功能
"""
import json
import os
import subprocess
import shutil
import httpx
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="FreqTrade 配置管理器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = Path("/freqtrade/user_data/config.json")
BACKUP_DIR = Path("/freqtrade/user_data/backups")
STRATEGY_DIR = Path("/freqtrade/user_data/strategies")

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
STRATEGY_DIR.mkdir(parents=True, exist_ok=True)

FREQTRADE_API_URL = "http://freqtrade:8080"


class ConfigModel(BaseModel):
    config: dict


class StrategyModel(BaseModel):
    name: str
    content: str


def backup_config():
    if CONFIG_PATH.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"config_{timestamp}.json"
        shutil.copy(CONFIG_PATH, backup_file)
        return backup_file
    return None


def validate_config(config: dict) -> tuple[bool, str]:
    required_fields = [
        "max_open_trades",
        "stake_currency",
        "stake_amount",
        "exchange",
        "timeframe"
    ]
    
    for field in required_fields:
        if field not in config:
            return False, f"缺少必要字段: {field}"
    
    if "exchange" in config:
        exchange = config["exchange"]
        if "name" not in exchange:
            return False, "缺少交易所名称"
        if "pair_whitelist" not in exchange or not exchange["pair_whitelist"]:
            return False, "交易对白名单不能为空"
    
    if config.get("dry_run") == False:
        if not config.get("exchange", {}).get("key"):
            return False, "实盘模式需要配置 API Key"
        if not config.get("exchange", {}).get("secret"):
            return False, "实盘模式需要配置 API Secret"
    
    return True, "配置验证通过"


async def reload_freqtrade_config() -> dict:
    """
    调用 FreqTrade 的 API 重新加载配置（热重载，无需重启）
    """
    try:
        async with httpx.AsyncClient() as client:
            # 首先尝试获取当前配置来验证 API 是否可用
            auth = None
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    api_config = config.get("api_server", {})
                    username = api_config.get("username", "freqtrade")
                    password = api_config.get("password", "")
                    if password:
                        auth = (username, password)
            
            # 调用 FreqTrade 的重载配置 API
            response = await client.post(
                f"{FREQTRADE_API_URL}/api/v1/reload_config",
                auth=auth,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "配置已热重载", "detail": response.json()}
            elif response.status_code == 401:
                return {"success": False, "message": "FreqTrade API 认证失败，请检查用户名密码"}
            else:
                return {"success": False, "message": f"FreqTrade API 返回错误: {response.status_code}"}
                
    except httpx.ConnectError:
        return {"success": False, "message": "无法连接到 FreqTrade，请确保服务正在运行"}
    except httpx.TimeoutException:
        return {"success": False, "message": "FreqTrade API 调用超时"}
    except Exception as e:
        return {"success": False, "message": f"热重载失败: {str(e)}"}


@app.get("/")
async def root():
    return {"message": "FreqTrade 配置管理器 API", "version": "2.0.0", "features": ["hot-reload"]}


@app.get("/api/config")
async def get_config():
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return {"success": True, "config": config}


@app.post("/api/config")
async def save_config(config_data: ConfigModel):
    config = config_data.config
    
    is_valid, message = validate_config(config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    backup_config()
    
    config["_updated_at"] = datetime.now().isoformat()
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    return {"success": True, "message": "配置保存成功", "backup_created": True}


@app.post("/api/config/save-and-reload")
async def save_and_reload_config(config_data: ConfigModel):
    """
    保存配置并立即热重载（无需重启 FreqTrade）
    """
    config = config_data.config
    
    is_valid, message = validate_config(config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    backup_config()
    
    config["_updated_at"] = datetime.now().isoformat()
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    # 调用 FreqTrade 的热重载 API
    reload_result = await reload_freqtrade_config()
    
    return {
        "success": True, 
        "message": "配置保存成功", 
        "backup_created": True,
        "reload_status": reload_result
    }


@app.post("/api/config/validate")
async def validate_config_endpoint(config_data: ConfigModel):
    is_valid, message = validate_config(config_data.config)
    return {"valid": is_valid, "message": message}


@app.post("/api/config/reload")
async def reload_config():
    """
    手动触发 FreqTrade 配置热重载
    """
    result = await reload_freqtrade_config()
    return result


@app.get("/api/backups")
async def list_backups():
    backups = []
    for backup_file in sorted(BACKUP_DIR.glob("config_*.json"), reverse=True):
        stat = backup_file.stat()
        backups.append({
            "filename": backup_file.name,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size
        })
    return {"success": True, "backups": backups[:20]}


@app.post("/api/backups/{filename}/restore")
async def restore_backup(filename: str):
    backup_file = BACKUP_DIR / filename
    if not backup_file.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    
    backup_config()
    
    shutil.copy(backup_file, CONFIG_PATH)
    
    # 恢复后自动热重载
    reload_result = await reload_freqtrade_config()
    
    return {
        "success": True, 
        "message": f"已恢复备份: {filename}",
        "reload_status": reload_result
    }


@app.get("/api/strategies")
async def list_strategies():
    strategies = []
    for strategy_file in STRATEGY_DIR.glob("*.py"):
        strategies.append({
            "name": strategy_file.stem,
            "filename": strategy_file.name,
            "modified_at": datetime.fromtimestamp(strategy_file.stat().st_mtime).isoformat()
        })
    return {"success": True, "strategies": strategies}


@app.get("/api/strategies/{name}")
async def get_strategy(name: str):
    strategy_file = STRATEGY_DIR / f"{name}.py"
    if not strategy_file.exists():
        raise HTTPException(status_code=404, detail="策略文件不存在")
    
    with open(strategy_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"success": True, "name": name, "content": content}


@app.post("/api/strategies")
async def save_strategy(strategy_data: StrategyModel):
    if not strategy_data.name.endswith(".py") and not strategy_data.name.endswith(".py"):
        strategy_name = strategy_data.name + ".py"
    else:
        strategy_name = strategy_data.name
    
    if "/" in strategy_name or "\\" in strategy_name:
        raise HTTPException(status_code=400, detail="策略名称不能包含路径分隔符")
    
    strategy_file = STRATEGY_DIR / strategy_name
    
    with open(strategy_file, "w", encoding="utf-8") as f:
        f.write(strategy_data.content)
    
    return {"success": True, "message": f"策略 {strategy_name} 保存成功"}


@app.delete("/api/strategies/{name}")
async def delete_strategy(name: str):
    strategy_file = STRATEGY_DIR / f"{name}.py"
    if not strategy_file.exists():
        raise HTTPException(status_code=404, detail="策略文件不存在")
    
    strategy_file.unlink()
    return {"success": True, "message": f"策略 {name} 已删除"}


@app.get("/api/status")
async def get_status():
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=freqtrade", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        status = result.stdout.strip()
        is_running = "Up" in status
        return {
            "success": True,
            "running": is_running,
            "status": status if status else "未运行"
        }
    except Exception as e:
        return {"success": False, "running": False, "error": str(e)}


@app.post("/api/restart")
async def restart_freqtrade():
    """
    完全重启 FreqTrade 容器（备用方案）
    """
    try:
        result = subprocess.run(
            ["docker", "restart", "freqtrade"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return {"success": True, "message": "FreqTrade 重启成功"}
    except FileNotFoundError:
        return {"success": False, "message": "Docker 命令不可用，请手动在服务器面板重启容器"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "重启超时，请手动重启"}
    except Exception as e:
        return {"success": False, "message": f"重启失败: {str(e)}"}
    
    return {"success": False, "message": "重启命令执行失败，请手动在 Dokploy 面板重启 FreqTrade 容器"}


@app.get("/api/logs")
async def get_logs(lines: int = 100):
    log_file = Path("/freqtrade/user_data/logs/freqtrade.log")
    if not log_file.exists():
        return {"success": True, "logs": "日志文件不存在"}
    
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(log_file)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {"success": True, "logs": result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/balance", response_class=HTMLResponse)
async def config_editor():
    html_path = Path("/app/static/config-editor.html")
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>配置编辑器页面不存在</h1>", status_code=404)


app.mount("/static", StaticFiles(directory="/app/static"), name="static")
