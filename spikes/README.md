# Spikes

Run these manually to smoke-test the scaffold outside of pytest. They are
useful when you're wiring up a real LLM or HTTP client and want to see
raw inputs/outputs without test ceremony.

```bash
python -m spikes.spike_send_receive_llm
python -m spikes.spike_send_receive_api
python -m spikes.spike_evaluate
```

Each spike prints to stdout; nothing is asserted.