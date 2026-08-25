from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalProcessorConfig:
    ttl_seconds: int
    nonce_ttl_seconds: int
    batch_size: int
    confirmation_timeout_seconds: int
    processing_timeout_seconds: int


EXTERNAL_PROCESSOR_CONFIG = ExternalProcessorConfig(
    ttl_seconds=300,
    nonce_ttl_seconds=600,
    batch_size=10,
    # ждём accept 5 минут
    confirmation_timeout_seconds=300,
    # ждём финальный result 3 суток: модерация в Честном Знаке может идти сутки и дольше
    processing_timeout_seconds=259200,
)


def get_external_processor_create_config() -> dict:
    return {
        'ttl_seconds': EXTERNAL_PROCESSOR_CONFIG.ttl_seconds,
        'nonce_ttl_seconds': EXTERNAL_PROCESSOR_CONFIG.nonce_ttl_seconds,
        'batch_size': EXTERNAL_PROCESSOR_CONFIG.batch_size,
        'confirmation_timeout_seconds': EXTERNAL_PROCESSOR_CONFIG.confirmation_timeout_seconds,
        'processing_timeout_seconds': EXTERNAL_PROCESSOR_CONFIG.processing_timeout_seconds,
    }