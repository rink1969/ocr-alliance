"""Utilities for testing the LLM connection used for OCR unification."""

from __future__ import annotations


def test_llm_connection(
    base_url: str,
    model: str,
    api_key: str,
    timeout: float = 30.0,
) -> tuple[bool, str]:
    """Send a minimal chat completion request and return whether it succeeded.

    Returns:
        A tuple of (success, message). The API key is never included in the
        returned message.
    """
    try:
        from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
    except ImportError as exc:
        return False, f"openai 包未安装: {exc}"

    if not base_url:
        return False, "LLM Base URL 不能为空"
    if not model:
        return False, "LLM Model 不能为空"

    client = OpenAI(
        base_url=base_url,
        api_key=api_key or "no-api-key",
        timeout=timeout,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "hi"},
            ],
            max_tokens=10,
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            return False, "连接成功，但模型返回了空内容"
        return True, f"连接成功，模型返回: {content.strip()[:100]}"
    except APITimeoutError:
        return False, "连接超时，请检查网络或 Base URL 是否正确"
    except APIConnectionError as exc:
        return False, f"无法连接到 LLM 服务: {exc}"
    except APIError as exc:
        return False, f"LLM API 错误: {exc.message}"
    except Exception as exc:  # noqa: BLE001
        return False, f"测试失败: {exc}"
