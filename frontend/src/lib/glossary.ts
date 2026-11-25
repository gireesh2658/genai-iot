export const TECHNICAL_GLOSSARY: Record<string, { title: string; summary: string }> = {
  CTGAN: {
    title: "CTGAN (Conditional Tabular GAN)",
    summary:
      "Deep generative model using Gaussian mixture normalization for continuous columns, Gumbel-Softmax outputs for discrete values, and PacGAN Wasserstein loss with gradient penalty.",
  },
  "Conditional Sampling": {
    title: "Conditional Generation",
    summary:
      "Constrains CTGAN sampling to specific attack categories or raw labels using SDV Condition vectors paired with 2x native-label preference filtering and domain repair.",
  },
  "Synthetic Data": {
    title: "Synthetic IoT Network Telemetry",
    summary:
      "Newly synthesized flow records learned from CICIoT2023 feature distributions rather than copied verbatim from real captures. Benign device bounds are applied post-sampling.",
  },
  TRTR: {
    title: "TRTR — Train Real, Test Real",
    summary:
      "Baseline anomaly detector fitted strictly on the 38,466 real CICIoT2023 training flows and scored on the disjoint 9,616 real validation flows.",
  },
  TSTR: {
    title: "TSTR — Train Synthetic, Test Real",
    summary:
      "Evaluates standalone transfer utility by training exclusively on 5,000 synthetic flows and benchmarking on real held-out validation traffic.",
  },
  "TSTR+R": {
    title: "TSTR+R — Real + Synthetic Augmentation",
    summary:
      "Appends synthetic flows to real training traffic (optimal 25% mix = 1,250 synthetic + 38,466 real) to improve rare-attack detection without drowning real priors.",
  },
  "Macro F1": {
    title: "Macro-Averaged F1 Score",
    summary:
      "Unweighted arithmetic mean of F1 across all 8 traffic classes. Treats rare threats (Brute Force, Web-based) equally alongside high-volume DDoS floods.",
  },
  "KS Statistic": {
    title: "Kolmogorov-Smirnov Statistic",
    summary:
      "Maximum vertical gap [0, 1] between real and synthetic empirical cumulative distributions. Lower values show closer marginal CDF alignment, though rare-class quotas intentionally shift marginal proportions.",
  },
  "Wasserstein Distance": {
    title: "Earth Mover's (Wasserstein-1) Distance",
    summary:
      "Cost to reshape the synthetic marginal distribution into the real marginal in raw feature units (e.g., packets/s or bytes). Sensitive to extreme attack packet bursts.",
  },
  "Jensen-Shannon Distance": {
    title: "Jensen-Shannon Distance",
    summary:
      "Symmetric, bounded [0, 1] discrete probability divergence measuring category and protocol flag balance against the reference set.",
  },
  "Pearson MACE": {
    title: "Mean Absolute Correlation Error",
    summary:
      "Mean off-diagonal absolute difference between real and synthetic 13×13 correlation matrices. Closer to 0 means pairwise relationships stay intact.",
  },
  "1-NN Distance": {
    title: "Nearest-Neighbor Distance",
    summary:
      "Standardized Euclidean distance from each synthetic record to its closest real training record. Values > 0 with 0 exact overlaps confirm novelty without claiming formal differential privacy.",
  },
};
