# FAQ

## Does ContextVault store my ChatGPT password?

No. Authentication occurs manually inside Google Chrome. ContextVault stores only the configured profile path/name and archive output.

## Does it bundle Chromium?

No. The frozen browser architecture uses official Google Chrome Stable through Playwright's Chrome channel or CDP.

## Is the archive suitable for RAG?

Yes. The archive includes lossless conversation JSON plus message-boundary RAG chunks, document metadata, keywords, and chunk mappings. It does not generate embeddings or provide semantic search in version 1.0.

## Can I view archives inside the application?

Version 1.0 opens `conversation.md` with the operating system and manages archive folders; a built-in archive viewer is outside the frozen scope.
