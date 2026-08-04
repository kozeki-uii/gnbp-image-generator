# 文件路径: config/config_mgr.py

import json
import os
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Optional

CONFIG_FILE = "GNBP_config.json"

# === 【修复 1】补全默认配置结构 ===
# 必须包含 profiles 和 prompts 列表，否则 UI 初始化读取时会报错
DEFAULT_CONFIG = {
    "current_profile_idx": 0,
    "current_prompt_idx": -1,
    "profiles": [
        {
            "name": "Configure API",
            "api_type": "gemini",
            "api_mode": "images",
            "api_url": "https://generativelanguage.googleapis.com",
            "api_key": "",
            "model": ""
        }
    ],
    "prompts": [
        {
            "name": "Example Prompt",
            "content": "A futuristic city with neon lights, cyberpunk style, high detail, 8k resolution"
        }
    ],
    "settings": {
        "aspect_ratio_idx": 2,
        "resolution_idx": 2,
        "gpt_size_idx": 0,
        "gpt_quality_idx": 0,
        "output_dir": "images",
        "window_size_idx": 1,
        "theme": "米黄",
        "show_preview": True,
        "batch_count": 1,
        "max_workers": 1,
        "history_limit": 60,
        "output_format_idx": 0,
        "moderation_idx": 0,
        "output_compression": 0,
        "sound_notify": True
    }
}

@dataclass
class GenConfig:
    api_url: str
    api_key: str
    model: str
    prompt: str
    aspect_ratio: str
    resolution: str
    output_dir: str
    api_type: str = "gemini"
    api_mode: str = "images"
    ref_images: List[str] = field(default_factory=list)
    mask_image: Optional[str] = None
    temperature: float = 0.9
    size: str = "1024x1024"
    quality: str = "auto"
    output_format: str = "png"
    output_compression: Optional[int] = None
    moderation: str = "auto"
    n: int = 1

@dataclass
class TaskData:
    id: str
    config: dict
    status: str
    prompt_short: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_str: str = ""
    path: Optional[str] = None
    error_msg: Optional[str] = None

class ConfigManager:
    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        # === 【修复 2】初始化逻辑增强 ===
        # 如果文件不存在，先加载默认值，然后【立即保存】生成文件
        if not os.path.exists(self.filepath):
            self.data = copy.deepcopy(DEFAULT_CONFIG)
            self.save_data() # 关键：创建物理文件
        else:
            self.data = self.load_data()

    def load_data(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "profiles" not in data or "settings" not in data:
                    return copy.deepcopy(DEFAULT_CONFIG)

                # Preserve user data while filling settings introduced by newer versions.
                merged = copy.deepcopy(DEFAULT_CONFIG)
                merged.update(data)
                merged["settings"] = copy.deepcopy(DEFAULT_CONFIG["settings"])
                if isinstance(data.get("settings"), dict):
                    merged["settings"].update(data["settings"])
                for profile in merged.get("profiles", []):
                    if isinstance(profile, dict):
                        profile["api_mode"] = (
                            profile.get("api_mode")
                            if profile.get("api_mode") in {"images", "responses"}
                            else "images"
                        )
                return merged
        except Exception as e:
            print(f"❌ Config Load Error: {e}")
            return copy.deepcopy(DEFAULT_CONFIG)

    def save_data(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Config Save Error: {e}")

    # --- Profile Ops ---
    def get_profiles(self):
        return self.data.get("profiles", [])

    def get_current_profile(self):
        idx = self.data.get("current_profile_idx", 0)
        profiles = self.get_profiles()
        # 增加鲁棒性：如果 idx 越界或者列表为空，返回默认空字典
        if not profiles:
            return {}
        if 0 <= idx < len(profiles):
            return profiles[idx]
        return profiles[0]

    def set_current_profile_idx(self, idx):
        self.data["current_profile_idx"] = idx
        self.save_data()

    def add_profile(self, name, api_type, url, key, model, api_mode="images"):
        if "profiles" not in self.data: self.data["profiles"] = []
        self.data["profiles"].append({
            "name": name,
            "api_type": api_type,
            "api_mode": api_mode if api_mode in {"images", "responses"} else "images",
            "api_url": url,
            "api_key": key,
            "model": model,
        })
        self.data["current_profile_idx"] = len(self.data["profiles"]) - 1
        self.save_data()

    def update_profile(self, idx, api_type, url, key, model, api_mode="images"):
        if "profiles" in self.data and 0 <= idx < len(self.data["profiles"]):
            self.data["profiles"][idx].update({
                "api_type": api_type,
                "api_mode": api_mode if api_mode in {"images", "responses"} else "images",
                "api_url": url,
                "api_key": key,
                "model": model,
            })
            self.save_data()

    def delete_profile(self, idx):
        if "profiles" in self.data and len(self.data["profiles"]) > 1 and 0 <= idx < len(self.data["profiles"]):
            del self.data["profiles"][idx]
            self.data["current_profile_idx"] = 0
            self.save_data()
            return True
        return False

    # --- Prompt Ops ---
    def get_prompts(self):
        return self.data.get("prompts", [])

    def add_prompt(self, name, content):
        if "prompts" not in self.data: self.data["prompts"] = []
        self.data["prompts"].append({"name": name, "content": content})
        self.save_data()

    def update_prompt(self, idx, content):
        if "prompts" in self.data and 0 <= idx < len(self.data["prompts"]):
            self.data["prompts"][idx]["content"] = content
            self.save_data()
            return True

    def delete_prompt(self, idx):
        if "prompts" in self.data and 0 <= idx < len(self.data["prompts"]):
            del self.data["prompts"][idx]
            self.save_data()

    # --- Settings Ops ---
    def update_settings(
        self,
        ratio_idx,
        res_idx,
        output_dir,
        gpt_size_idx=None,
        gpt_quality_idx=None,
        output_format_idx=None,
        moderation_idx=None,
        output_compression=None,
    ):
        if "settings" not in self.data: self.data["settings"] = {}
        self.data["settings"].update(
            {"aspect_ratio_idx": ratio_idx, "resolution_idx": res_idx, "output_dir": output_dir})
        if gpt_size_idx is not None:
            self.data["settings"]["gpt_size_idx"] = gpt_size_idx
        if gpt_quality_idx is not None:
            self.data["settings"]["gpt_quality_idx"] = gpt_quality_idx
        if output_format_idx is not None:
            self.data["settings"]["output_format_idx"] = output_format_idx
        if moderation_idx is not None:
            self.data["settings"]["moderation_idx"] = moderation_idx
        if output_compression is not None:
            self.data["settings"]["output_compression"] = output_compression
        self.save_data()

    def get_settings(self):
        return self.data.get("settings", DEFAULT_CONFIG["settings"])
