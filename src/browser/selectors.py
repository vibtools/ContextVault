"""Centralized resilient selectors for ChatGPT browser extraction."""

CONVERSATION_LINK_SELECTOR = "a[href*='/c/'], a[href*='/conversation/']"
MESSAGE_SELECTOR = "[data-message-author-role], [data-testid^='conversation-turn']"
LOADING_SELECTOR = "[aria-busy='true'], [data-loading='true'], .result-streaming"
TITLE_SELECTORS = (
    "main h1",
    "header h1",
    "title",
)
