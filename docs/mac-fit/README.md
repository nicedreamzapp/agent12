# Will it fit my Mac

One page per MLX model, answering the question every Apple Silicon download comes down to:
how much unified memory does this actually need, and which Mac holds it.

Live: https://nicedreamzapp.github.io/mac-fit/

## Where the numbers come from

- **Download size** is summed from the `.safetensors` files in the model repo root, as
  reported by the Hugging Face API. Root level only, so repos that ship several quants in
  subfolders are not counted as one giant model.
- **KV cache** is computed from that model's own `config.json`:
  `2 tensors x layers x KV heads x head dim x 2 bytes (fp16) x tokens`. The formula is
  printed on every page so you can check it.
- **Runtime overhead** is a flat 1.2 GB for Python, MLX, the tokenizer and activations,
  which is what I see on my own runs.
- **Which Macs fit** assumes MLX can wire about 75% of unified memory, leaving the rest to
  macOS and your apps.

Parameter counts are deliberately left off. Hugging Face reports safetensors element
counts, and MLX packs quantized weights into `uint32`, so that figure reads several times
the true parameter count on exactly these repos.

## What is not here

Tokens per second. That needs a real run on real silicon, and I am not going to publish a
number I have not measured. Open an issue naming your model and I will run it and add the
result along with the command used.

## Taking a page down

Open an issue or email matt@ineedhemp.com and it comes down the same day. No questions.

Built by [Matt Macosko](https://github.com/nicedreamzapp), who publishes
[MLX quants](https://huggingface.co/divinetribe) and wrote
[claude-code-local](https://github.com/nicedreamzapp/claude-code-local).
