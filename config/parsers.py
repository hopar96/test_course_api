from __future__ import annotations
import json
from typing import Any
from rest_framework.parsers import JSONParser
from django.conf import settings


class TextPlainJSONParser(JSONParser):
    """
    text/plain Content-Type으로 전송된 JSON 데이터를 파싱하는 파서
    """
    media_type = 'text/plain'
    
    def parse(self, stream, media_type=None, parser_context=None):
        """
        text/plain으로 전송된 JSON 데이터를 파싱
        """
        try:
            # 스트림에서 데이터 읽기
            data = stream.read().decode('utf-8')
            # JSON 파싱
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"잘못된 JSON 형식입니다: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"인코딩 오류입니다: {e}")

