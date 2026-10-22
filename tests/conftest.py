"""Run tests with synthetic credentials, never the developer's production env."""
import os

os.environ.update({
    "JWT_SECRET": "synapse-test-secret-with-at-least-32-characters",
    "OPENAI_API_KEY": "test-openai-key",
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "SURREAL_URL": "ws://127.0.0.1:18081/rpc",
    "SURREAL_NS": "security_tests",
    "SURREAL_DB": "security_tests",
    "SURREAL_USER": "test",
    "SURREAL_PASS": "test",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGSMITH_TRACING": "false",
})
