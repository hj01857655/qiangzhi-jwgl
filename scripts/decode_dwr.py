#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWR 请求体解码工具
用于解析和解码 DWR (Direct Web Remoting) 请求参数
"""

import urllib.parse
import base64
import re

def decode_url_encoded(encoded_str):
    """URL 解码"""
    return urllib.parse.unquote(encoded_str)

def parse_dwr_body(body):
    """解析 DWR 请求体"""
    lines = body.strip().split('\n')
    parsed = {}
    
    for line in lines:
        if '=' in line:
            key, value = line.split('=', 1)
            parsed[key] = value
    
    return parsed

def decode_dwr_param(param_value):
    """尝试解码 DWR 参数"""
    # 去除 string: 前缀
    if param_value.startswith('string:'):
        param_value = param_value[7:]
    
    # URL 解码
    decoded = decode_url_encoded(param_value)
    
    return decoded

def analyze_encrypted_string(encrypted_str):
    """分析加密字符串的可能格式"""
    print("\n" + "="*80)
    print("加密字符串分析")
    print("="*80)
    
    print(f"\n原始长度: {len(encrypted_str)}")
    print(f"前50个字符: {encrypted_str[:50]}...")
    print(f"后50个字符: ...{encrypted_str[-50:]}")
    
    # 检查是否为 Base64
    try:
        base64_decoded = base64.b64decode(encrypted_str)
        print(f"\n✓ 可能是 Base64 编码")
        print(f"  Base64 解码后 (前100字节): {base64_decoded[:100]}")
        try:
            print(f"  Base64 解码为文本: {base64_decoded.decode('utf-8')[:200]}")
        except:
            print(f"  Base64 解码为文本: (无法解码为 UTF-8)")
    except Exception as e:
        print(f"\n✗ 不是标准 Base64: {e}")
    
    # 统计字符分布
    char_types = {
        'uppercase': sum(1 for c in encrypted_str if c.isupper()),
        'lowercase': sum(1 for c in encrypted_str if c.islower()),
        'digits': sum(1 for c in encrypted_str if c.isdigit()),
        'special': sum(1 for c in encrypted_str if not c.isalnum())
    }
    
    print(f"\n字符分布:")
    for char_type, count in char_types.items():
        print(f"  {char_type}: {count} ({count/len(encrypted_str)*100:.1f}%)")
    
    # 检查特殊字符
    special_chars = set(c for c in encrypted_str if not c.isalnum())
    print(f"\n特殊字符: {special_chars}")
    
    # 查找重复模式
    print(f"\n查找重复模式 (2-5字符):")
    for length in range(2, 6):
        patterns = {}
        for i in range(len(encrypted_str) - length + 1):
            pattern = encrypted_str[i:i+length]
            patterns[pattern] = patterns.get(pattern, 0) + 1
        
        # 显示出现3次以上的模式
        repeated = {k: v for k, v in patterns.items() if v >= 3}
        if repeated:
            top_patterns = sorted(repeated.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  {length}字符模式: {top_patterns}")

def main():
    # DWR 请求体
    body = """callCount=1
page=/xszhxxAction.do?method=allXjztck
httpSessionId=04FC1A1A4D854C917FED71FB011112E2
scriptSessionId=F62D09EE2EB2C13CA728C19EC4CBAFE4715
c0-scriptName=dwrMonitor
c0-methodName=ldLoadOper
c0-id=0
c0-param0=string:%23!%40RjcHNVM4EnNUNQJzAiZGKAIrUmRGelV5Vz1LO1BgRHZROhAjUXoHaUM5ADUANVF7FzxQL1ExQCFVdVwuRTxRP0YnB3BGTAULVl0XGwIPU14AWEVKU1dXXEAmXiRSPUQqU3EQLVEuEiZUZwInFRxRXwJaUl1GQlVeV15LSlBZU1lGMwU6RiQFc0MkACUAbkY6AGFQZ1FyQCtVJlwwRSBRPlFzEHpTdBIxVGYXNQImUzYXKFIwU35XP0A4XmZSY0RpUysHJEZhBz5DYQAiFSBRcgJeRUlRVVVeV15LSlBZU1lGTQVbUTcSeFYwFzICbEY6AGFQZ0ZlVz9VLVxkRXRRO1E3EGdTPQVvQ2ECLxU5USYXI1I4UztAIVcjXnZSOEQ%2FU2EHYUYoB2dUdhd0AHZGLQA8RWNRNlUvQHBcZVB5U3lGSQVYUV8SH1ZdAAwVGFNeF09SXUYqVztVMUtjUjdRKlE6EDRTIAVyQ2ECLwJ1RicCP0UmUT9ANld3XmdFZVM2UyMHP0YsByNUPBdqADRRZBcoUDJGa1ciQChcMVAiRCJRcwU4US4SJlZlAGsVdVN5ACtFOlM2QGJXaktjUjhRKkZ0B2FTegVrQzkCNwI3RisCN1J0RkZVXUBJXF1FTFNZU1gQTlFfBwpUXxcbAA1RNBcoUDJRfEAoVS1Lc1JjRClRNwV8RigFclYwAGAVfVN3AGxFY1N5V2VAZ152RSRTPkYgB3BTPhJuVGYCNgJoRiYCfVIuRj9Vd1dqS2NQd0R2UXQQZ1E3B21DJQAlAG5RLRd2UGdRMkAmVXtcP0U2UTxGIAdwRigFb1Z0FzoCLlMkADRFL1M7VzZANF52UjZELlMiEDNRPxJ4VDUCcxUxUT4CIFI6Ri9Vd1cxSzFQP1M9RmQFOEY5BTFDcABrAGBGawB4UFtRVkBLVVxcXUVMUVtRWhBOU10SH1RfFxsCZ1M5FyJSdFN2Vz9AOF5mUmNEKVM1B35GOQd7Q3EANhUhUWQCOkUnUXxVald3S3xQcFM%2FRjYFclFpEjZWPRdhAiZGLAAkUDpGJ1d1VVhcXkVMUVtRWhBOU10FCENIAg4VGFFcF09SXVMxQDBXd14zUipELlMiByRGMgcjVH4XYQBhRi4ANEUgUShVd0BxXHRQNlMiRisFP1F2Em5WLAA1FSJTZxd3UnRGPFc9VTBLMVI3UXJRKxA%2FU2QFMkNxAjYCKEY6AitFc1FvQHJXZl4%2FRSFTcFNsB3BGKwd7VGYXIwBqUTEXaFAuRjNXZUBzXGRQYUQuUTcFclE3EnhWMAAlFWlTLwBhRXBTbkBzV3lLL1IhUTZGMwc4U3QFPENhAjgCJkZrAnpSdEZGVV1ASVxdRUxTWVNYEE5RXwcKVF8XGwANUTQXKFAyUXxAalU%2FSztSYkR2UT0FNkZvBWpWJwBrFXVTdwBsRWNTYVd1QC9eJEVlU29GZAc5UycSNlQ4AnICakYuAnpSfUZrVVpXXUtKUFlETlFaEE5RXwcKQ0gAagB2UTEXI1AkUXxAIFUsXHRFL1EqRnQHYUZvBXtWLRd6
c0-param1=string:'21'%2C%40'21'%2C%40'21'%2C%40''%2C%40''
batchId=1"""

    print("="*80)
    print("DWR 请求体解析")
    print("="*80)
    
    # 解析请求体
    parsed = parse_dwr_body(body)
    
    print("\n基本信息:")
    print(f"  调用次数: {parsed.get('callCount', 'N/A')}")
    print(f"  页面: {parsed.get('page', 'N/A')}")
    print(f"  Session ID: {parsed.get('httpSessionId', 'N/A')}")
    print(f"  Script Session ID: {parsed.get('scriptSessionId', 'N/A')}")
    
    print(f"\n方法调用:")
    print(f"  Script名称: {parsed.get('c0-scriptName', 'N/A')}")
    print(f"  方法名称: {parsed.get('c0-methodName', 'N/A')}")
    
    # 解码参数
    print(f"\n参数解码:")
    
    # 参数0
    if 'c0-param0' in parsed:
        param0_decoded = decode_dwr_param(parsed['c0-param0'])
        print(f"\n  c0-param0 (URL解码后):")
        print(f"  长度: {len(param0_decoded)}")
        print(f"  内容: {param0_decoded}")
        
        # 分析加密字符串
        analyze_encrypted_string(param0_decoded)
    
    # 参数1
    if 'c0-param1' in parsed:
        param1_decoded = decode_dwr_param(parsed['c0-param1'])
        print(f"\n  c0-param1 (URL解码后):")
        print(f"  {param1_decoded}")
        
        # 尝试解析为数组
        param1_parts = param1_decoded.replace("'", "").split(',@')
        print(f"  解析为数组: {param1_parts}")
    
    print("\n" + "="*80)
    print("解码完成")
    print("="*80)
    
    # 提示可能的加密方式
    print("\n可能的加密/编码方式:")
    print("1. 自定义 XOR 加密")
    print("2. 简单替换密码")
    print("3. Base64 变种")
    print("4. AES/DES 加密后的 Base64")
    print("5. 服务端特定的加密算法")
    print("\n建议:")
    print("- 检查网页的 JavaScript 源代码，查找加密函数")
    print("- 查看 DWR 的配置文件")
    print("- 尝试抓取加密过程的 JavaScript 调用")

if __name__ == "__main__":
    main()
