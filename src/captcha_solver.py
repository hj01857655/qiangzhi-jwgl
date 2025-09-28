#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证码自动识别模块
支持多种OCR引擎识别验证码
"""

import logging
from PIL import Image, ImageEnhance, ImageFilter
import io
from typing import Optional, Dict, Any

# PIL兼容性补丁（参考qz项目）
try:
    # 为了兼容新版本的Pillow，添加ANTIALIAS别名
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

class CaptchaSolver:
    """验证码识别器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ocr_engines = []
        self._init_ocr_engines()
    
    def _init_ocr_engines(self):
        """初始化OCR引擎"""
        # 加载ddddocr（主要引擎）
        try:
            import ddddocr
            self.ddddocr = ddddocr.DdddOcr()
            self.ocr_engines.append('ddddocr')
            self.logger.info("已加载ddddocr引擎")
        except ImportError:
            self.logger.error("ddddocr未安装！请安装: pip install ddddocr")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        简化的图像预处理，避免版本兼容问题
        
        Args:
            image: PIL图像对象
            
        Returns:
            预处理后的图像
        """
        try:
            # 简化处理，只进行基本转换
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return image
            
        except Exception as e:
            self.logger.warning(f"图像预处理失败: {e}")
            return image
    
    def recognize_with_ddddocr(self, image_data: bytes) -> Optional[str]:
        """
        使用ddddocr识别验证码（修复版本兼容性）
        
        Args:
            image_data: 图像二进制数据
            
        Returns:
            识别结果或None
        """
        if 'ddddocr' not in self.ocr_engines:
            return None
        
        try:
            # 直接使用原始字节数据，避免PIL处理
            self.logger.info(f"正在使用ddddocr识别验证码...")
            result = self.ddddocr.classification(image_data)
            
            if not result:
                self.logger.warning("ddddocr返回空结果")
                return None
            
            # 清理结果：只保留字母数字
            cleaned = ''.join(c for c in str(result) if c.isalnum())
            
            self.logger.info(f"ddddocr识别原始结果: '{result}'")
            self.logger.info(f"ddddocr清理后结果: '{cleaned}'")
            
            return cleaned if cleaned else None
            
        except Exception as e:
            self.logger.error(f"ddddocr识别异常: {type(e).__name__}: {str(e)}")
            # 记录更详细的错误信息
            import traceback
            self.logger.debug(f"ddddocr详细错误: {traceback.format_exc()}")
            return None
    
    def recognize_with_tesseract(self, image: Image.Image) -> Optional[str]:
        """
        使用tesseract识别验证码
        
        Args:
            image: PIL图像对象
            
        Returns:
            识别结果或None
        """
        if 'tesseract' not in self.ocr_engines:
            return None
        
        try:
            # tesseract配置
            config = '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            result = self.pytesseract.image_to_string(image, config=config).strip()
            
            # 清理结果
            result = ''.join(c for c in result if c.isalnum())
            self.logger.info(f"tesseract识别结果: {result}")
            return result if result else None
            
        except Exception as e:
            self.logger.error(f"tesseract识别失败: {e}")
            return None
    
    def solve_captcha(self, image_data: bytes) -> Dict[str, Any]:
        """
        自动识别验证码
        
        Args:
            image_data: 验证码图像二进制数据
            
        Returns:
            识别结果字典
        """
        if not self.ocr_engines:
            return {
                'success': False,
                'message': '没有可用的OCR引擎，请安装ddddocr或pytesseract',
                'result': None
            }
        
        try:
            # 直接使用ddddocr识别，避免PIL处理
            self.logger.info(f"开始识别验证码，数据大小: {len(image_data)} bytes")
            
            if 'ddddocr' in self.ocr_engines:
                result = self.recognize_with_ddddocr(image_data)
                if result:
                    # 严格限制为4位
                    if len(result) >= 4:
                        cleaned_result = result[:4]  # 取前4位
                        return {
                            'success': True,
                            'result': cleaned_result,
                            'engine': 'ddddocr',
                            'message': f'识别成功: {cleaned_result} (原始: {result})'
                        }
                    elif len(result) == 3:
                        # 放宽到3位，但警告
                        self.logger.warning(f"识别结果只有3位: {result}")
                        return {
                            'success': True,
                            'result': result,
                            'engine': 'ddddocr',
                            'message': f'识别成功(只有3位): {result}'
                        }
                    else:
                        self.logger.warning(f"ddddocr识别结果太短: {result} (长度: {len(result)})")
                else:
                    self.logger.warning("ddddocr识别结果为空")
            else:
                return {
                    'success': False,
                    'result': None,
                    'message': '所有引擎都未能识别出有效结果'
                }
                
        except Exception as e:
            self.logger.error(f"验证码识别过程出错: {e}")
            return {
                'success': False,
                'result': None,
                'message': f'识别过程出错: {str(e)}'
            }
    
    def get_available_engines(self) -> list:
        """获取可用的OCR引擎列表"""
        return self.ocr_engines.copy()