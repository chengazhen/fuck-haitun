# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: cursor_pro_keep_alive.py
# Bytecode version: 3.9.0beta5 (3425)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import hashlib
import platform
import random
import uuid
import subprocess
import requests
import time
import sys
import os
import json
from proxy_pool import ProxyPool


def generate_device_id():
    """生成设备识别码"""
    device_id = "5d" + "".join(random.choices("0123456789abcdef", k=30))
    return device_id


def update_cursor_config(email, access_token, refresh_token):
    """更新 Cursor 配置文件"""
    try:
        config_path = os.path.expanduser("~/.cursor/config.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        config["email"] = email
        config["accessToken"] = access_token
        config["refreshToken"] = refresh_token
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"\n更新配置失败: {str(e)}")
        return False


def refresh_account(device_id):
    """刷新账号"""
    try:
        proxy_pool = ProxyPool()
        working_proxy = proxy_pool.get_working_proxy()

        if not working_proxy:
            print("\n未找到可用代理，将使用直连方式")
            working_proxy = None
        else:
            print(f"\n使用代理: {working_proxy['http']}")
    except Exception as e:
        print(f"\n代理获取失败: {str(e)}，将使用直连方式")
        working_proxy = None

    try:
        response = requests.post(
            "http://2000.run:3000/api/refresh_account",
            json={"device_id": device_id},
            timeout=10,
            proxies=working_proxy,
        )

        if response.status_code != 200:
            print(f"\n服务器响应错误，状态码: {response.status_code}")
            if response.text:
                print("\n错误详情:")
                print("-" * 50)
                print(response.text[:500].strip())  # 展示更多内容，并去除首尾空格
                print("-" * 50)
            return False

        try:
            data = response.json()
        except ValueError:
            print("\n服务器返回的数据格式错误")
            print("\n响应详情:")
            print("-" * 50)
            # 尝试格式化显示响应内容
            response_lines = response.text[:500].strip().split("\n")
            for line in response_lines:
                if line.strip():  # 只显示非空行
                    print(f"| {line.strip()}")
            print("-" * 50)
            return False

        # 检查响应码
        if data.get("code") != 0:
            error_msg = data.get("msg", "未知错误")
            print(f"\n刷新失败: {error_msg}")
            return False

        # 验证返回数据完整性
        account_data = data.get("data")
        if not account_data:
            print("\n服务器返回数据缺失")
            return False

        required_fields = ["email", "access_token", "refresh_token"]
        missing_fields = [
            field for field in required_fields if field not in account_data
        ]
        if missing_fields:
            print(f"\n账号数据缺失字段: {', '.join(missing_fields)}")
            return False

        # 数据验证通过，保存认证信息
        print("\nCursor 激活成功！")
        print(f"当前账号: {account_data['email']}")

        auth_manager = CursorAuthManager()
        if auth_manager.update_auth(
            email=account_data["email"],
            access_token=account_data["access_token"],
            refresh_token=account_data["refresh_token"],
        ):
            print("授权信息已保存")
            if account_data.get("is_trial"):
                print("\n注意: 这是试用版，仅可使用一次")
                print("建议购买会员获得完整体验")
            return True

        print("保存授权信息失败")
        return False

    except requests.exceptions.Timeout:
        print("\n连接服务器超时")
    except requests.exceptions.ConnectionError:
        print("\n无法连接到服务器")
    except Exception as e:
        print(f"\n发生错误: {str(e)}")

    return False


class CursorAuthManager:
    def __init__(self):
        self.auth_file = "cursor_auth.json"
        self.ensure_auth_file()

    def ensure_auth_file(self):
        """确保认证文件存在，如果不存在则创建一个空的JSON文件"""
        if not os.path.exists(self.auth_file):
            with open(self.auth_file, "w") as f:
                json.dump([], f)

    def save_auth(self, auth_data):
        """保存认证数据到JSON文件，采用追加模式"""
        try:
            # 读取现有数据
            existing_data = []
            if os.path.exists(self.auth_file):
                with open(self.auth_file, "r") as f:
                    existing_data = json.load(f)

            # 检查是否已存在相同的数据
            if auth_data not in existing_data:
                existing_data.append(auth_data)

            # 写入更新后的数据
            with open(self.auth_file, "w") as f:
                json.dump(existing_data, f, indent=4)
            return True
        except Exception as e:
            print(f"保存认证数据时出错: {str(e)}")
            return False

    def get_auth(self):
        """获取认证数据"""
        try:
            if os.path.exists(self.auth_file):
                with open(self.auth_file, "r") as f:
                    data = json.load(f)
                    return data[-1] if data else None  # 返回最新的认证数据
            return None
        except Exception as e:
            print(f"读取认证数据时出错: {str(e)}")
            return None

    def update_auth(self, email, access_token, refresh_token):
        """更新认证信息"""
        auth_data = {
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        # 保存认证数据
        return self.save_auth(auth_data)


def main():
    """主函数，支持指定执行次数和时间间隔自动运行"""
    try:
        # 获取执行次数和时间间隔
        times = 1
        interval_minutes = 0

        if len(sys.argv) > 2:
            times = int(sys.argv[1])
            interval_minutes = int(sys.argv[2])
        else:
            while True:
                try:
                    times = int(input("\n请输入要执行的次数 (默认1次): ") or "1")
                    if times < 1:
                        print("执行次数必须大于0，请重新输入")
                        continue

                    interval_minutes = int(
                        input("\n请输入执行间隔时间(分钟，默认0表示不循环): ") or "0"
                    )
                    if interval_minutes < 0:
                        print("间隔时间不能为负数，请重新输入")
                        continue
                    break
                except ValueError:
                    print("请输入有效的数字！")

        while True:  # 外层循环处理定时执行
            current_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"\n开始执行批次 - 当前时间: {current_time}")

            print(f"\n将执行 {times} 次刷新操作...")
            success_count = 0

            for i in range(times):
                print(f"\n正在执行第 {i + 1}/{times} 次刷新...")
                device_id = generate_device_id()
                if refresh_account(device_id):
                    success_count += 1

                # 如果不是最后一次执行，则等待一段时间
                if i < times - 1:
                    wait_time = random.randint(3, 8)
                    print(f"\n等待 {wait_time} 秒后执行下一次刷新...")
                    time.sleep(wait_time)

            print(
                f"\n执行完成！成功 {success_count} 次，失败 {times - success_count} 次"
            )

            # 如果不需要定时执行，直接退出
            if interval_minutes <= 0:
                break

            # 计算下次执行时间并等待
            next_time = time.strftime(
                "%H:%M:%S", time.localtime(time.time() + interval_minutes * 60)
            )
            print(
                f"\n本次批次执行完成，将在 {next_time} （{interval_minutes}分钟后）进行下一次执行"
            )
            print("按 Ctrl+C 可以终止程序")

            try:
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\n用户取消等待，程序终止")
                return

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n发生错误: {str(e)}")


if __name__ == "__main__":
    main()
