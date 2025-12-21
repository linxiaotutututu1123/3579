# DL Module Model Card

## Model Overview

**Module**: V4PRO Deep Learning Strategy Module
**Version**: v4.2
**Phase**: Phase 6 B-Class Model Layer
**Last Updated**: 2025-12-22

---

## Architecture

### Directory Structure

```
src/strategy/dl/
├── __init__.py                 # Module exports
├── features.py                 # Feature extraction (original)
├── model.py                    # TinyMLP model (original)
├── policy.py                   # Inference policy (original)
├── weights.py                  # Model loading utilities (original)
├── data/                       # Data layer (NEW)
│   ├── __init__.py
│   ├── sequence_handler.py     # Sequence data processing
│   └── dataset.py              # Financial dataset abstraction
├── models/                     # Model layer (NEW)
│   ├── __init__.py
│   └── lstm.py                 # Enhanced LSTM with attention
├── training/                   # Training layer (NEW)
│   ├── __init__.py
│   └── trainer.py              # Training loop and callbacks
└── factors/                    # Factor layer (NEW)
    ├── __init__.py
    └── ic_calculator.py        # Information Coefficient metrics
```

### Components

| Layer | Component | Description | Status |
|-------|-----------|-------------|--------|
| Data | SequenceHandler | Time series window generation | NEW |
| Data | FinancialDataset | PyTorch-compatible dataset | NEW |
| Model | EnhancedLSTM | LSTM with attention and residual | NEW |
| Model | TinyMLP | Simple MLP baseline | Existing |
| Training | TradingModelTrainer | Training loop with callbacks | NEW |
| Training | EarlyStopping | Early stopping mechanism | NEW |
| Factor | ICCalculator | Information Coefficient | NEW |

---

## Model Specifications

### EnhancedLSTM

```python
LSTMConfig(
    input_dim=3,           # Feature dimensions
    hidden_dim=64,         # Hidden layer size
    num_layers=2,          # LSTM layers
    output_dim=1,          # Output dimension
    dropout=0.1,           # Dropout rate
    bidirectional=False,   # Bidirectional mode
    use_attention=True,    # Self-attention
    use_residual=True      # Residual connections
)
```

**Architecture Features**:
- Multi-layer LSTM with configurable depth
- Self-attention mechanism for long-term dependencies
- Residual connections for gradient flow
- Layer normalization for stability
- Tanh output activation for [-1, 1] range

**Parameter Count**: ~50K-200K (depending on configuration)

---

## Military Rule Compliance

| Rule | Requirement | Implementation |
|------|-------------|----------------|
| M7 | Deterministic replay | Seed-based RNG, hash verification |
| M3 | Complete audit logging | Computation logs, model hashes |
| M19 | Risk attribution | IC tracking, factor metrics |
| M26 | Testing standards | 95%+ coverage target |

---

## Quality Gates

### IC Threshold
- **Gate**: IC >= 0.05
- **Metric**: Spearman correlation
- **Validation**: `ICCalculator.validate_model()`

### Test Coverage
- **Target**: >= 95%
- **Scenarios**: 27 DL scenarios
- **Tests**: `tests/test_dl_module.py`

---

## Usage Examples

### Data Pipeline

```python
from src.strategy.dl import (
    SequenceConfig,
    SequenceHandler,
    FinancialDataset,
    DatasetConfig,
)

# Configure sequence handler
seq_config = SequenceConfig(
    window_size=60,
    features=("returns", "volume", "range"),
    normalization=NormalizationMethod.ZSCORE,
)

# Build sequences
handler = SequenceHandler(seq_config)
windows = handler.build_sequences(bars)

# Create dataset
dataset = FinancialDataset(DatasetConfig(sequence_config=seq_config))
dataset.fit(bars, targets)
train, val, test = dataset.get_splits()
```

### Model Training

```python
from src.strategy.dl import (
    EnhancedLSTM,
    LSTMConfig,
    TradingModelTrainer,
    TrainerConfig,
)

# Create model
model = EnhancedLSTM(LSTMConfig(input_dim=3, hidden_dim=64))

# Train
trainer = TradingModelTrainer(
    model,
    TrainerConfig(epochs=100, early_stopping_patience=10),
)
history = trainer.fit(train_loader, val_loader)
```

### IC Validation

```python
from src.strategy.dl import ICCalculator, validate_ic_gate

# Validate model
calculator = ICCalculator()
result = calculator.compute(predictions, returns)

if result.passes_threshold:
    print(f"Model passed IC gate: {result.ic:.4f}")
else:
    print(f"Model failed IC gate: {result.ic:.4f}")

# Convenience function
passed = validate_ic_gate(predictions, returns, threshold=0.05)
```

---

## Scenarios Coverage

| Scenario ID | Description | Status |
|-------------|-------------|--------|
| DL.DATA.SEQ.BUILD | Sequence building determinism | Implemented |
| DL.DATA.SEQ.NORMALIZE | Sequence normalization | Implemented |
| DL.DATA.SEQ.WINDOW | Sliding window generation | Implemented |
| DL.DATA.DATASET.CREATE | Dataset creation | Implemented |
| DL.DATA.DATASET.SPLIT | Dataset splitting | Implemented |
| DL.DATA.DATASET.SHUFFLE | Deterministic shuffle | Implemented |
| DL.MODEL.LSTM.FORWARD | LSTM forward pass | Implemented |
| DL.MODEL.LSTM.ATTENTION | Attention mechanism | Implemented |
| DL.MODEL.LSTM.RESIDUAL | Residual connections | Implemented |
| DL.TRAIN.LOOP | Training loop | Implemented |
| DL.TRAIN.EARLY_STOP | Early stopping | Implemented |
| DL.TRAIN.CHECKPOINT | Checkpoint saving | Implemented |
| DL.TRAIN.AUDIT | Training audit logs | Implemented |
| DL.FACTOR.IC.COMPUTE | IC computation | Implemented |
| DL.FACTOR.IC.DECAY | IC decay analysis | Implemented |
| DL.FACTOR.IC.RANK | Rank IC | Implemented |

---

## Performance Metrics

### Training Performance
- Batch size: 32-128
- Training time: ~1-5 min per epoch (CPU)
- Memory usage: ~100-500 MB

### Inference Performance
- Latency: < 1ms per sample (CPU)
- Throughput: 10,000+ samples/sec (CPU)

---

## Dependencies

```
torch>=2.0.0
numpy>=1.21.0
scipy>=1.7.0
```

---

## Changelog

### v4.2 (2025-12-22)
- Added data layer (sequence_handler, dataset)
- Added model layer (EnhancedLSTM with attention)
- Added training layer (trainer, early_stopping)
- Added factor layer (ic_calculator)
- Full military rule compliance
- Comprehensive test coverage

---

## References

- V4PRO_IMPROVEMENT_DESIGN_v1.2.md: D6 Phase 6 B-Class Model Plan
- V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md: System upgrade directive
- Military Rules: M1-M33 compliance requirements
