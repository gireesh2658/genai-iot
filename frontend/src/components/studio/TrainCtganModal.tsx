"use client";

import React, { useEffect, useState } from "react";
import { Cpu, X } from "lucide-react";
import { api } from "@/lib/api";
import { CTGANTrainResponse } from "@/lib/types";
import { IconButton, PrimaryButton, SecondaryButton } from "@/components/ui/Button";
import { useToast } from "@/components/ui/ToastProvider";

export function TrainCtganModal({
  open,
  onClose,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: (res: CTGANTrainResponse) => void;
}) {
  const { pushToast } = useToast();
  const [modelId, setModelId] = useState("ctgan_custom_v1");
  const [epochs, setEpochs] = useState(10);
  const [sampleSize, setSampleSize] = useState(2000);
  const [batchSize, setBatchSize] = useState(200);
  const [randomSeed, setRandomSeed] = useState(42);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open) return null;

  const idBad = !/^[a-zA-Z0-9_-]{3,40}$/.test(modelId.trim());
  const batchBad = batchSize % 10 !== 0 || batchSize < 50 || batchSize > 500;
  const sampleBad = sampleSize < 500 || sampleSize > 38466 || sampleSize < batchSize;
  const epochsBad = epochs < 1 || epochs > 150;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (idBad || batchBad || sampleBad || epochsBad) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await api.trainCtganModel({
        model_id: modelId.trim(),
        epochs,
        sample_size: sampleSize,
        batch_size: batchSize,
        random_seed: randomSeed,
      });
      pushToast(
        "success",
        `Saved CTGAN checkpoint '${res.model_id}'`,
        `Fitted ${res.epochs} epochs on ${res.training_rows} rows in ${res.elapsed_seconds}s`
      );
      onSuccess(res);
      onClose();
    } catch (error: any) {
      setErr(error.message || "CTGAN training failed");
      pushToast("error", "CTGAN training failed", error.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="train-ctgan-title"
    >
      <div
        className="fixed inset-0 bg-[#2B3748]/25 backdrop-blur-[1px]"
        onClick={() => !busy && onClose()}
        aria-hidden="true"
      />

      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-full max-w-lg space-y-4 rounded-2xl border border-hairline bg-surface p-6 shadow-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-tint text-brand">
              <Cpu className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="train-ctgan-title" className="text-base font-bold text-ink">
                Fit New CTGAN Checkpoint
              </h2>
              <p className="text-xs text-ink-secondary">
                Trains a fresh CPU checkpoint on stratified CICIoT2023 flows; never overwrites <code className="font-mono">ctgan_full_v1</code>.
              </p>
            </div>
          </div>
          <IconButton label="Close CTGAN trainer" onClick={() => !busy && onClose()}>
            <X className="h-4 w-4" />
          </IconButton>
        </div>

        <div className="rounded-xl border border-[#F1D5A6] bg-[#FEF5E7] px-3.5 py-2.5 text-xs text-[#844F0C]">
          Runs synchronously on host CPU (a 150-epoch fit takes ~1.67h on full 38,466 rows; start with 5–15 epochs on 1,000–3,000 rows). Wait for request completion.
        </div>

        {err && (
          <div role="alert" className="rounded-xl border border-[#F2C3BF] bg-[#FDECEC] px-3.5 py-2.5 text-xs font-semibold text-[#9A332D]">
            {err}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="new-ctgan-id" className="mb-1 block text-xs font-semibold text-ink-secondary">
              Checkpoint Identifier (unique name)
            </label>
            <input
              id="new-ctgan-id"
              required
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              className="studio-input font-mono text-xs"
            />
            {idBad && (
              <p className="mt-1 text-[11px] text-[#BF4840]">3–40 chars (alphanumeric, _ or -).</p>
            )}
          </div>

          <div>
            <label htmlFor="ctgan-epochs" className="mb-1 block text-xs font-semibold text-ink-secondary">
              Epochs (1–150)
            </label>
            <input
              id="ctgan-epochs"
              type="number"
              min={1}
              max={150}
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value) || 1)}
              className="studio-input font-mono tabular-nums"
            />
          </div>

          <div>
            <label htmlFor="ctgan-sample" className="mb-1 block text-xs font-semibold text-ink-secondary">
              Training Pool Size (500–38,466)
            </label>
            <input
              id="ctgan-sample"
              type="number"
              min={500}
              max={38466}
              step={250}
              value={sampleSize}
              onChange={(e) => setSampleSize(Number(e.target.value) || 500)}
              className="studio-input font-mono tabular-nums"
            />
          </div>

          <div>
            <label htmlFor="ctgan-batch" className="mb-1 block text-xs font-semibold text-ink-secondary">
              Batch Size (multiple of pac=10)
            </label>
            <input
              id="ctgan-batch"
              type="number"
              min={50}
              max={500}
              step={10}
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value) || 50)}
              className="studio-input font-mono tabular-nums"
            />
            {batchBad && (
              <p className="mt-1 text-[11px] text-[#BF4840]">Must be 50–500 and divisible by 10.</p>
            )}
          </div>

          <div>
            <label htmlFor="ctgan-seed" className="mb-1 block text-xs font-semibold text-ink-secondary">
              Random Seed
            </label>
            <input
              id="ctgan-seed"
              type="number"
              value={randomSeed}
              onChange={(e) => setRandomSeed(Number(e.target.value) || 42)}
              className="studio-input font-mono tabular-nums"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2.5 border-t border-hairline pt-4">
          <SecondaryButton type="button" disabled={busy} onClick={onClose}>
            Cancel
          </SecondaryButton>
          <PrimaryButton
            type="submit"
            loading={busy}
            disabled={idBad || batchBad || sampleBad || epochsBad}
          >
            {busy ? "Fitting on CPU..." : "Fit & Save Checkpoint"}
          </PrimaryButton>
        </div>
      </form>
    </div>
  );
}
