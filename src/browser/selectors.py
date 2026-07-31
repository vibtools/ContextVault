"""Centralized resilient selectors for ChatGPT browser extraction."""

CONVERSATION_LINK_SELECTOR = "a[href*='/c/'], a[href*='/conversation/']"
MESSAGE_SELECTOR = "[data-message-author-role], [data-testid^='conversation-turn'], [data-message-id], main article"
PRIMARY_MESSAGE_SELECTOR = "[data-message-author-role]"
FALLBACK_MESSAGE_SELECTOR = "[data-testid^='conversation-turn']"
MESSAGE_ID_SELECTOR = "[data-message-id]"
CONVERSATION_CONTAINER_SELECTOR = "main, [role='main']"
APPLICATION_ROOT_SELECTOR = "#__next, main, [role='main']"
LOADING_SELECTOR = (
    "main [aria-busy='true'], main [data-loading='true'], "
    "[role='main'] [aria-busy='true'], [role='main'] [data-loading='true'], "
    "main [role='progressbar'], [role='main'] [role='progressbar'], "
    "main [data-testid*='loading' i], main [data-testid*='spinner' i], .result-streaming"
)
STREAMING_SELECTOR = (
    ".result-streaming, [data-is-streaming='true'], [data-testid='stop-button'], "
    "button[aria-label*='stop generating' i]"
)
MODEL_SELECTORS = (
    "[data-testid*='model-switcher']",
    "button[aria-label*='model' i]",
    "button[data-testid*='model']",
)
WORKSPACE_SELECTORS = (
    "[data-testid*='workspace']",
    "button[aria-label*='workspace' i]",
    "nav [data-testid*='account']",
)
TITLE_SELECTORS = (
    "main h1",
    "header h1",
    "title",
)
