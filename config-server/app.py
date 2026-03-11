"""
FreqTrade 配置管理 API - 完全独立于 FreqTrade 运行
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
    """验证配置是否有效"""
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


async def check_freqtrade_status() -> dict:
    """检查 FreqTrade 服务状态"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FREQTRADE_API_URL}/api/v1/ping",
                timeout=5.0
            )
            if response.status_code == 200:
                return {"running": True, "message": "FreqTrade 运行正常"}
            return {"running": False, "message": "FreqTrade 响应异常"}
    except httpx.ConnectError:
        return {"running": False, "message": "无法连接到 FreqTrade"}
    except Exception as e:
        return {"running": False, "message": f"检查失败: {str(e)}"}


async def reload_freqtrade_config() -> dict:
    """
    调用 FreqTrade 的 API 重新加载配置（热重载，无需重启）
    如果 FreqTrade 未运行或调用失败，不会影响配置保存
    """
    try:
        async with httpx.AsyncClient() as client:
            # 从配置文件中读取认证信息
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
                return {"success": True, "message": "✅ 配置已热重载，立即生效", "detail": response.json()}
            elif response.status_code == 401:
                return {"success": False, "message": "⚠️ FreqTrade API 认证失败，配置已保存但需手动重启"}
            else:
                return {"success": False, "message": f"⚠️ FreqTrade API 返回错误: {response.status_code}，配置已保存但需手动重启"}
                
    except httpx.ConnectError:
        return {"success": False, "message": "⚠️ 无法连接到 FreqTrade，配置已保存，启动 FreqTrade 后将自动加载新配置"}
    except httpx.TimeoutException:
        return {"success": False, "message": "⚠️ FreqTrade API 调用超时，配置已保存"}
    except Exception as e:
        return {"success": False, "message": f"⚠️ 热重载失败: {str(e)}，配置已保存"}


@app.get("/")
async def root():
    return {
        "message": "FreqTrade 配置管理器 API", 
        "version": "2.0.0", 
        "features": ["hot-reload", "independent"],
        "note": "此服务完全独立于 FreqTrade，可单独运行"
    }


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    freqtrade_status = await check_freqtrade_status()
    config_exists = CONFIG_PATH.exists()
    
    return {
        "success": True,
        "config_server": "running",
        "freqtrade": freqtrade_status,
        "config_exists": config_exists,
        "config_path": str(CONFIG_PATH)
    }


@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    if not CONFIG_PATH.exists():
        # 如果配置不存在，返回默认配置
        default_config = get_default_config()
        return {"success": True, "config": default_config, "is_default": True}
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {"success": True, "config": config, "is_default": False}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="配置文件格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {str(e)}")


def get_default_config():
    """获取默认配置模板"""
    return {
        "max_open_trades": 3,
        "stake_currency": "USDT",
        "stake_amount": 30,
        "tradable_balance_ratio": 0.99,
        "fiat_display_currency": "CNY",
        "timeframe": "5m",
        "dry_run": True,
        "dry_run_wallet": 1000,
        "cancel_open_orders_on_exit": False,
        "unfilledtimeout": {
            "entry": 10,
            "exit": 10,
            "exit_timeout_count": 0,
            "unit": "minutes"
        },
        "entry_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1,
            "price_last_balance": 0.0,
            "check_depth_of_market": {"enabled": False, "bids_to_ask_delta": 1}
        },
        "exit_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1
        },
        "exchange": {
            "name": "binance",
            "key": "",
            "secret": "",
            "ccxt_config": {},
            "ccxt_async_config": {},
            "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
            "pair_blacklist": []
        },
        "pairlists": [{"method": "StaticPairList"}],
        "telegram": {"enabled": False, "token": "", "chat_id": ""},
        "api_server": {
            "enabled": True,
            "listen_ip_address": "0.0.0.0",
            "listen_port": 8080,
            "verbosity": "error",
            "jwt_secret_key": "freqtrade_jwt_secret_key_change_me",
            "ws_token": "freqtrade_ws_token_change_me",
            "CORS_origins": [],
            "username": "freqtrade",
            "password": "KJDD9773LJKDkjkj"
        },
        "bot_name": "freqtrade_bot",
        "initial_state": "running",
        "force_entry_enable": True,
        "internals": {"process_throttle_secs": 5}
    }


@app.post("/api/config")
async def save_config(config_data: ConfigModel):
    """仅保存配置，不触发重载"""
    config = config_data.config
    
    is_valid, message = validate_config(config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    backup_config()
    config["_updated_at"] = datetime.now().isoformat()
    
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return {"success": True, "message": "✅ 配置保存成功", "backup_created": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@app.post("/api/config/save-and-reload")
async def save_and_reload_config(config_data: ConfigModel):
    """
    保存配置并尝试热重载
    即使 FreqTrade 未运行或重载失败，配置也会保存成功
    """
    config = config_data.config
    
    is_valid, message = validate_config(config)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # 先备份和保存配置
    backup_config()
    config["_updated_at"] = datetime.now().isoformat()
    
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")
    
    # 尝试热重载（不影响保存结果）
    reload_result = await reload_freqtrade_config()
    
    return {
        "success": True, 
        "message": "配置保存成功", 
        "backup_created": True,
        "reload_status": reload_result
    }


@app.post("/api/config/validate")
async def validate_config_endpoint(config_data: ConfigModel):
    """验证配置有效性"""
    is_valid, message = validate_config(config_data.config)
    return {"valid": is_valid, "message": message}


@app.post("/api/config/reload")
async def reload_config():
    """手动触发 FreqTrade 配置热重载"""
    result = await reload_freqtrade_config()
    return result


@app.get("/api/backups")
async def list_backups():
    """列出所有配置备份"""
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
    """恢复配置备份"""
    backup_file = BACKUP_DIR / filename
    if not backup_file.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    
    backup_config()
    shutil.copy(backup_file, CONFIG_PATH)
    
    # 尝试热重载
    reload_result = await reload_freqtrade_config()
    
    return {
        "success": True, 
        "message": f"✅ 已恢复备份: {filename}",
        "reload_status": reload_result
    }


@app.get("/api/strategies")
async def list_strategies():
    """列出所有策略"""
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
    """获取策略代码"""
    strategy_file = STRATEGY_DIR / f"{name}.py"
    if not strategy_file.exists():
        raise HTTPException(status_code=404, detail="策略文件不存在")
    
    with open(strategy_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"success": True, "name": name, "content": content}


@app.post("/api/strategies")
async def save_strategy(strategy_data: StrategyModel):
    """保存策略"""
    if not strategy_data.name.endswith(".py"):
        strategy_name = strategy_data.name + ".py"
    else:
        strategy_name = strategy_data.name
    
    if "/" in strategy_name or "\\" in strategy_name:
        raise HTTPException(status_code=400, detail="策略名称不能包含路径分隔符")
    
    strategy_file = STRATEGY_DIR / strategy_name
    
    with open(strategy_file, "w", encoding="utf-8") as f:
        f.write(strategy_data.content)
    
    return {"success": True, "message": f"✅ 策略 {strategy_name} 保存成功"}


@app.delete("/api/strategies/{name}")
async def delete_strategy(name: str):
    """删除策略"""
    strategy_file = STRATEGY_DIR / f"{name}.py"
    if not strategy_file.exists():
        raise HTTPException(status_code=404, detail="策略文件不存在")
    
    strategy_file.unlink()
    return {"success": True, "message": f"✅ 策略 {name} 已删除"}


@app.get("/api/logs")
async def get_logs(lines: int = 100):
    """获取 FreqTrade 日志"""
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
    """配置编辑器页面"""
    html_path = Path("/app/static/config-editor.html")
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>配置编辑器页面不存在</h1>", status_code=404)


app.mount("/static", StaticFiles(directory="/app/static"), name="static")
