import random
import requests
from typing import Optional, List, Dict
import os


class ProxyPool:
    def __init__(self, proxy_file: str = "out.txt"):
        self.proxy_file = proxy_file
        self.proxies: List[str] = []
        self.load_proxies()

    def load_proxies(self) -> None:
        """从文件加载代理列表"""
        if not os.path.exists(self.proxy_file):
            raise FileNotFoundError(f"代理文件 {self.proxy_file} 不存在")

        with open(self.proxy_file, "r") as f:
            self.proxies = [line.strip() for line in f if line.strip()]

    def get_random_proxy(self) -> Dict[str, str]:
        """随机获取一个代理"""
        if not self.proxies:
            raise ValueError("代理池为空")

        proxy = random.choice(self.proxies)
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    def test_proxy(self, proxy: Dict[str, str], timeout: int = 5) -> bool:
        """测试代理是否可用"""
        try:
            response = requests.get(
                "http://www.baidu.com", proxies=proxy, timeout=timeout
            )
            return response.status_code == 200
        except:
            return False

    def get_working_proxy(self, max_attempts: int = 5) -> Optional[Dict[str, str]]:
        """获取一个可用的代理"""
        for _ in range(max_attempts):
            proxy = self.get_random_proxy()
            if self.test_proxy(proxy):
                return proxy
        return None


# 使用示例
if __name__ == "__main__":
    proxy_pool = ProxyPool()

    # 获取一个随机代理
    proxy = proxy_pool.get_random_proxy()
    print(f"随机代理: {proxy}")

    # 获取一个可用的代理
    working_proxy = proxy_pool.get_working_proxy()
    if working_proxy:
        print(f"可用代理: {working_proxy}")
    else:
        print("未找到可用代理")
