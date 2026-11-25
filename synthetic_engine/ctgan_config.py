"""
IoTSynth AI - CTGAN Configuration Module (Phase 5.2)

Provides strongly typed, validated configuration dataclasses for CTGAN
generative modeling under SDV 2.2.0 and CTGAN 0.13.0.
Enforces:
  - Default CPU execution (Intel Core i5-13420H compatibility).
  - Strict PacGAN compatibility invariant: batch_size % pac == 0.
  - Positive layer dimensions and learning rates.
  - Pre-defined Pilot Run and Full Training presets.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class CTGANConfig:
    """Configuration specification for CTGAN model training and architecture.

    Attributes:
        epochs: Number of training epochs. Must be >= 1.
        batch_size: Number of samples per training batch. Must be positive and
            a strict multiple of ``pac``.
        pac: Number of samples grouped together for the PacGAN discriminator.
            Must be >= 1 and divide ``batch_size`` evenly.
        generator_dim: Architecture of the generator MLP layers.
        discriminator_dim: Architecture of the discriminator MLP layers.
        generator_lr: Learning rate for the generator Adam optimizer.
        discriminator_lr: Learning rate for the discriminator Adam optimizer.
        embedding_dim: Size of the categorical embedding vectors.
        generator_decay: Weight decay (L2 penalty) for the generator.
        discriminator_decay: Weight decay (L2 penalty) for the discriminator.
        discriminator_steps: Number of discriminator training steps per generator step.
        log_frequency: Whether to log loss values periodically.
        cuda: Whether to attempt GPU acceleration. Defaults to False (CPU execution).
        random_seed: Seed for PyTorch, NumPy, and Python RNGs.
        verbose: Whether SDV / CTGAN prints training progress to stdout.
        enforce_min_max_values: Whether SDV clamps sampled numerical values to
            observed minimum and maximum bounds.
        enforce_rounding: Whether SDV rounds sampled numerical values to match
            the observed precision of training columns.
    """

    epochs: int = 300
    batch_size: int = 500
    pac: int = 10
    generator_dim: Tuple[int, ...] = (128, 128)
    discriminator_dim: Tuple[int, ...] = (128, 128)
    generator_lr: float = 2e-4
    discriminator_lr: float = 2e-4
    embedding_dim: int = 128
    generator_decay: float = 1e-6
    discriminator_decay: float = 1e-6
    discriminator_steps: int = 1
    log_frequency: bool = True
    cuda: bool = False
    random_seed: Optional[int] = 42
    verbose: bool = False
    enforce_min_max_values: bool = True
    enforce_rounding: bool = True

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate all configuration parameters against architectural invariants.

        Raises:
            ValueError: If any parameter violates physical or architectural constraints.
        """
        # Epochs validation
        if not isinstance(self.epochs, int) or self.epochs < 1:
            raise ValueError(f"epochs must be a positive integer >= 1, got: {self.epochs}")

        # Pac validation
        if not isinstance(self.pac, int) or self.pac < 1:
            raise ValueError(f"pac must be a positive integer >= 1, got: {self.pac}")

        # Batch size validation
        if not isinstance(self.batch_size, int) or self.batch_size < 1:
            raise ValueError(f"batch_size must be a positive integer >= 1, got: {self.batch_size}")

        # PacGAN compatibility invariant: batch_size % pac == 0
        if self.batch_size % self.pac != 0:
            raise ValueError(
                f"PacGAN compatibility invariant violated: batch_size ({self.batch_size}) "
                f"must be an exact multiple of pac ({self.pac}). "
                f"Got remainder {self.batch_size % self.pac}."
            )

        # Dimension validations
        if not isinstance(self.generator_dim, (tuple, list)) or not self.generator_dim:
            raise ValueError(f"generator_dim must be a non-empty tuple of integers, got: {self.generator_dim}")
        for dim in self.generator_dim:
            if not isinstance(dim, int) or dim <= 0:
                raise ValueError(f"Each generator_dim layer must be a positive integer, got: {dim}")

        if not isinstance(self.discriminator_dim, (tuple, list)) or not self.discriminator_dim:
            raise ValueError(f"discriminator_dim must be a non-empty tuple of integers, got: {self.discriminator_dim}")
        for dim in self.discriminator_dim:
            if not isinstance(dim, int) or dim <= 0:
                raise ValueError(f"Each discriminator_dim layer must be a positive integer, got: {dim}")

        if not isinstance(self.embedding_dim, int) or self.embedding_dim <= 0:
            raise ValueError(f"embedding_dim must be a positive integer, got: {self.embedding_dim}")

        # Learning rate validations
        if not isinstance(self.generator_lr, (int, float)) or self.generator_lr <= 0:
            raise ValueError(f"generator_lr must be a positive float, got: {self.generator_lr}")
        if not isinstance(self.discriminator_lr, (int, float)) or self.discriminator_lr <= 0:
            raise ValueError(f"discriminator_lr must be a positive float, got: {self.discriminator_lr}")

        # Decay validations
        if not isinstance(self.generator_decay, (int, float)) or self.generator_decay < 0:
            raise ValueError(f"generator_decay must be non-negative, got: {self.generator_decay}")
        if not isinstance(self.discriminator_decay, (int, float)) or self.discriminator_decay < 0:
            raise ValueError(f"discriminator_decay must be non-negative, got: {self.discriminator_decay}")

        # Discriminator steps validation
        if not isinstance(self.discriminator_steps, int) or self.discriminator_steps < 1:
            raise ValueError(f"discriminator_steps must be a positive integer >= 1, got: {self.discriminator_steps}")

        # CUDA validation
        if not isinstance(self.cuda, bool):
            raise ValueError(f"cuda must be a boolean, got: {type(self.cuda).__name__}")

        # Random seed validation
        if self.random_seed is not None and not isinstance(self.random_seed, int):
            raise ValueError(f"random_seed must be an integer or None, got: {type(self.random_seed).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "pac": self.pac,
            "generator_dim": list(self.generator_dim),
            "discriminator_dim": list(self.discriminator_dim),
            "generator_lr": self.generator_lr,
            "discriminator_lr": self.discriminator_lr,
            "embedding_dim": self.embedding_dim,
            "generator_decay": self.generator_decay,
            "discriminator_decay": self.discriminator_decay,
            "discriminator_steps": self.discriminator_steps,
            "log_frequency": self.log_frequency,
            "cuda": self.cuda,
            "random_seed": self.random_seed,
            "verbose": self.verbose,
            "enforce_min_max_values": self.enforce_min_max_values,
            "enforce_rounding": self.enforce_rounding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CTGANConfig":
        """Instantiate CTGANConfig from dictionary."""
        gen_dim = data.get("generator_dim", (128, 128))
        disc_dim = data.get("discriminator_dim", (128, 128))
        return cls(
            epochs=int(data.get("epochs", 300)),
            batch_size=int(data.get("batch_size", 500)),
            pac=int(data.get("pac", 10)),
            generator_dim=tuple(gen_dim) if isinstance(gen_dim, list) else gen_dim,
            discriminator_dim=tuple(disc_dim) if isinstance(disc_dim, list) else disc_dim,
            generator_lr=float(data.get("generator_lr", 2e-4)),
            discriminator_lr=float(data.get("discriminator_lr", 2e-4)),
            embedding_dim=int(data.get("embedding_dim", 128)),
            generator_decay=float(data.get("generator_decay", 1e-6)),
            discriminator_decay=float(data.get("discriminator_decay", 1e-6)),
            discriminator_steps=int(data.get("discriminator_steps", 1)),
            log_frequency=bool(data.get("log_frequency", True)),
            cuda=bool(data.get("cuda", False)),
            random_seed=data.get("random_seed", 42),
            verbose=bool(data.get("verbose", False)),
            enforce_min_max_values=bool(data.get("enforce_min_max_values", True)),
            enforce_rounding=bool(data.get("enforce_rounding", True)),
        )

    def to_sdv_kwargs(self) -> Dict[str, Any]:
        """Convert configuration to keyword arguments expected by SDV's CTGANSynthesizer."""
        return {
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "pac": self.pac,
            "generator_dim": tuple(self.generator_dim),
            "discriminator_dim": tuple(self.discriminator_dim),
            "generator_lr": self.generator_lr,
            "discriminator_lr": self.discriminator_lr,
            "embedding_dim": self.embedding_dim,
            "generator_decay": self.generator_decay,
            "discriminator_decay": self.discriminator_decay,
            "discriminator_steps": self.discriminator_steps,
            "log_frequency": self.log_frequency,
            "verbose": self.verbose,
            "enable_gpu": self.cuda,  # SDV maps GPU via enable_gpu parameter
            "enforce_min_max_values": self.enforce_min_max_values,
            "enforce_rounding": self.enforce_rounding,
        }

    # ------------------------------------------------------------------
    # Pre-configured Architecture Presets
    # ------------------------------------------------------------------

    @classmethod
    def get_pilot_config(cls, random_seed: Optional[int] = 42) -> "CTGANConfig":
        """Pre-flight pilot configuration for CPU environment.

        Designed for quick pipeline verification (< 2 min):
          - 5 epochs
          - batch_size: 100 (100 % 10 == 0)
          - pac: 10
          - generator_dim: (128, 128)
          - discriminator_dim: (128, 128)
          - cuda: False (CPU execution)
        """
        return cls(
            epochs=5,
            batch_size=100,
            pac=10,
            generator_dim=(128, 128),
            discriminator_dim=(128, 128),
            generator_lr=2e-4,
            discriminator_lr=2e-4,
            embedding_dim=128,
            cuda=False,
            random_seed=random_seed,
            verbose=False,
        )

    @classmethod
    def get_full_training_config(cls, random_seed: Optional[int] = 42) -> "CTGANConfig":
        """Production full-training configuration for CPU environment.

        Designed for deep generative modeling on 16 GB RAM CPU:
          - 150 epochs
          - batch_size: 250 (250 % 10 == 0)
          - pac: 10
          - generator_dim: (128, 128)
          - discriminator_dim: (128, 128)
          - cuda: False (CPU execution)
        """
        return cls(
            epochs=150,
            batch_size=250,
            pac=10,
            generator_dim=(128, 128),
            discriminator_dim=(128, 128),
            generator_lr=2e-4,
            discriminator_lr=2e-4,
            embedding_dim=128,
            cuda=False,
            random_seed=random_seed,
            verbose=False,
        )
