import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000"

def benchmark_single_request():
    """测试单个请求的响应时间"""
    times = []
    
    for i in range(5):
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False
            }
        )
        end = time.time()
        
        if response.status_code == 200:
            times.append(end - start)
            print(f"Request {i+1}: {end-start:.2f}s")
    
    if times:
        print(f"\nAverage response time: {statistics.mean(times):.2f}s")
        print(f"Min: {min(times):.2f}s, Max: {max(times):.2f}s")

def benchmark_concurrent_requests():
    """测试并发性能"""
    def make_request(i):
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": f"Request {i}"}],
                "stream": False
            }
        )
        return time.time() - start, response.status_code
    
    concurrent_levels = [1, 3, 5]
    
    for level in concurrent_levels:
        print(f"\nTesting with {level} concurrent requests...")
        with ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(make_request, i) for i in range(level)]
            times = []
            for future in as_completed(futures):
                duration, status = future.result()
                times.append(duration)
            
            print(f"Average time: {statistics.mean(times):.2f}s")
            print(f"Total time: {max(times):.2f}s")

if __name__ == "__main__":
    print("Running benchmark tests...")
    print("\n1. Single Request Benchmark")
    benchmark_single_request()
    
    print("\n2. Concurrent Request Benchmark")
    benchmark_concurrent_requests()