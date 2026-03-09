# Ulysses Sequence Parallelism: Training with Million-Token Contexts

Training large language models on long sequences has become essential for building capable AI systems. As models are increasingly used for tasks like document analysis, code understanding, complex reasoning, and RAG workloads, the need to process sequences of hundreds of thousands—or even millions—of tokens has grown dramatically. To put this in perspective, an average book is roughly 250k tokens, so training on multi-document contexts or book-length inputs requires handling sequences well beyond what fits on a single GPU. However, training with such long contexts presents significant memory challenges: the attention computation scales quadratically with sequence length, quickly exceeding GPU memory for contexts beyond tens of thousands of tokens.

Ulysses Sequence Parallelism (part of the Arctic Long Sequence Training protocol from Snowflake AI Research) provides an elegant solution by distributing the attention computation across multiple GPUs through attention head parallelism. In this post, we'll explore how Ulysses works and how it's been integrated across the Hugging Face ecosystem—from Accelerate to the Transformers Trainer and TRL's SFTTrainer.

## The Challenge of Long Sequence Training

The attention mechanism in transformers scales quadratically with sequence length. For very long sequences (32k+ tokens), even with FlashAttention, training still pushes the limits of single-GPU memory.

Long-context training matters for document understanding, large codebases, reasoning-heavy models, and retrieval-augmented generation. Traditional data parallelism doesn't solve this because each GPU still needs the full sequence inside the attention block.

## How Ulysses Works

Ulysses Sequence Parallelism takes a different approach: it splits the sequence across devices, then uses all-to-all communication so each GPU computes a subset of attention heads.

The core flow is:

- Sequence sharding across GPUs.
- Local QKV projection.
- All-to-all communication to redistribute per-head data.
- Local attention computation with FlashAttention or SDPA.
- A second all-to-all to restore sequence-sharded format.
- Local output projection.

The main advantage over Ring Attention is lower communication volume per GPU and better latency characteristics on supported hardware.

## Integration Across the Hugging Face Stack

The article walks through how Ulysses is integrated into Accelerate via ParallelismConfig and DeepSpeedSequenceParallelConfig, then into Transformers Trainer and TRL's SFTTrainer.

It also covers practical configuration details such as `sp_size`, `sp_backend`, `sp_attn_implementation`, sequence divisibility, padding, loss aggregation, and 2D SP × DP setups.

## Best Practices and Benchmarks

The write-up recommends matching sequence length divisibility to `sp_size`, preferring Flash Attention, combining SP with DeepSpeed ZeRO, and using allocator settings that reduce memory fragmentation.

Benchmark examples on H100 80GB GPUs show that SP can cut per-GPU memory enough to reach much longer context lengths, while also improving token throughput at larger sequence sizes.

## Why It Matters

This is not just an algorithm note: it turns long-context training from a niche systems trick into something accessible through mainstream Hugging Face tooling. That lowers the barrier for teams that want to train or fine-tune models on book-scale, repository-scale, or multi-document inputs.
