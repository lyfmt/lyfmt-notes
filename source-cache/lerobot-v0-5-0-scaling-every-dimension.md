# LeRobot v0.5.0: Scaling Every Dimension

With over 200 merged PRs and over 50 new contributors since v0.4.0, LeRobot v0.5.0 is our biggest release yet — expanding in every direction at once. More robots (including our first humanoid), more policies (including the comeback of autoregressive VLAs), faster datasets, simulation environments you can load straight from the Hub, and a modernized codebase running on Python 3.12 and Transformers v5. Whether you're training policies in simulation or deploying them on real hardware, v0.5.0 has something for you.

## TL;DR

LeRobot v0.5.0 adds full Unitree G1 humanoid support (whole-body control models), new policies –including Pi0-FAST autoregressive VLAs and Real-Time Chunking for responsive inference–, and streaming video encoding that eliminates wait times between recording episodes. The release also introduces EnvHub for loading simulation environments from the Hugging Face Hub, NVIDIA IsaacLab-Arena integration, and a major codebase modernization with Python 3.12+, Transformers v5, and third-party policy plugins.

## Hardware: More Robots Than Ever

The biggest hardware addition in this release: full Unitree G1 humanoid support. This is LeRobot's first humanoid integration, and it's comprehensive:

- Locomotion: Walk, navigate, and move through environments.
- Manipulation: Perform dexterous object manipulation tasks.
- Teleoperation: Control the G1 remotely with an intuitive teleoperation interface.
- Whole-Body Control (WBC): Coordinate locomotion and manipulation simultaneously for complex, real-world tasks.

![](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/lerobot-blog/release-v0.5.0/unitree_bosswalk.JPG)

We've added support for the OpenArm robot and its companion OpenArm Mini teleoperator. Both support bi-manual configurations.

More hardware additions include Earth Rover, OMX Robot, SO-100/SO-101 consolidation, and CAN bus motor controller support via RobStride and Damiao.

## Policies: A Growing Model Zoo

This release brings six new policies and techniques into LeRobot.

### Pi0-FAST: Autoregressive VLAs

Pi0-FAST brings autoregressive Vision-Language-Action models to LeRobot with FAST (Frequency-space Action Sequence Tokenization), using a Gemma 300M-based action expert and configurable decoding.

### Real-Time Chunking (RTC)

Real-Time Chunking is an inference-time technique from Physical Intelligence that makes flow-matching policies dramatically more responsive by continuously blending new predictions with in-progress actions.

### Wall-X / X-VLA / SARM / PEFT

Wall-X builds on Qwen2.5-VL with flow-matching action prediction. X-VLA brings a Florence2-based VLA. SARM targets long-horizon tasks with stage-aware reward modeling. PEFT support allows fine-tuning large VLAs using LoRA and related techniques.

![](https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/lerobot-blog/release-v0.5.0/sarm_community.gif)

## Datasets: Faster Recording, Faster Training

Streaming video encoding removes wait time between recording episodes. Under the hood, the release also improves image training speed by up to 10x, encoding by up to 3x, and adds more dataset editing operations, subtask support, and image-to-video conversion.

## EnvHub: Environments from the Hub

EnvHub lets LeRobot load simulation environments directly from the Hugging Face Hub instead of requiring local environment package setup. The release also integrates NVIDIA IsaacLab-Arena for GPU-accelerated simulation.

## Codebase: A Modern Foundation

The codebase now targets Python 3.12+, Transformers v5, third-party policy plugins, remote Rerun visualization, improved installation flow, and versioned docs.

## Community & Ecosystem

The release also mentions a refreshed Discord, better GitHub templates and automated labeling, ICLR 2026 paper acceptance, an updated Visualizer, and LeRobot Annotation Studio.
