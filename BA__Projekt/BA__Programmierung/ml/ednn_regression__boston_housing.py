# BA__Projekt/BA__Programmierung/ml/ednn_regression__boston_housing.py

import os
import torch

from BA__Programmierung.ml.datasets.dataset__torch__boston_housing import DatasetTorchBostonHousing
from BA__Programmierung.ml.metrics.metrics_registry import MetricsRegistry
from BA__Programmierung.ml.utils.training_utils import load_model_checkpoint, train_with_early_stopping
from models.model__generic import GenericRegressor
from torch.utils.data import DataLoader, random_split

def main():
    # Load dataset
    dataset = DatasetTorchBostonHousing(
        csv_path="assets/data/raw/dataset__boston-housing/dataset__boston-housing.csv"
    )

    # Train/val split
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )
    train_loader = DataLoader(train_set, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=16, shuffle=False)

    # Device and input dimension
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_dim = 13  # Boston Housing has 13 features

    # Base model config
    base_config = {
        "input_dim": input_dim,
        "hidden_dims": [64, 64],
        "output_type": "evidential",
        "use_dropout": False,
        "dropout_p": 0.2,
        "flatten_input": False,
        "use_batchnorm": False,
        "activation_name": "relu",
    }

    # Ensemble and training config
    n_models = 5
    seed = 42
    metric_bundles = MetricsRegistry.get_metric_bundles()
    loss_modes = ["mse"]

    # Base path for saving models
    model_save_base = "assets/models/pth/ednn_regression__boston_housing"

    print("Available tokens: ")
    print(metric_bundles)

    for loss_mode in loss_modes:
        model_save_dir = os.path.join(model_save_base, loss_mode)
        os.makedirs(model_save_dir, exist_ok=True)

        for i in range(n_models):
            torch.manual_seed(seed + i)
            model = GenericRegressor(**base_config).to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

            model_path = os.path.join(model_save_dir, f"model_{i}.pth")
            print(f"[{loss_mode.upper()}] Training model {i + 1}/{n_models}...")

            # Load checkpoint if it exists
            checkpoint, checkpoint_exists = load_model_checkpoint(model, optimizer, model_path, device)

            # Decide which token to use for metrics
            if loss_mode in ["nll", "full", "variational", "kl"]:
                metrics_token = "uq"
            elif loss_mode in ["mse", "abs"]:
                metrics_token = "regression"
            else:
                metrics_token = None  # or "probabilistic" depending on your setup

            if not checkpoint_exists:
                # If no checkpoint exists, train the model from scratch
                train_with_early_stopping(
                    model=model,
                    train_loader=train_loader,
                    val_loader=val_loader,
                    optimizer=optimizer,
                    model_path=model_path,
                    device=device,
                    epochs=100,
                    patience=10,
                    loss_mode=loss_mode,
                    metrics_token=metrics_token,
                )
            else:
                # If checkpoint exists, resume training from the checkpoint
                train_with_early_stopping(
                    model=model,
                    train_loader=train_loader,
                    val_loader=val_loader,
                    optimizer=optimizer,
                    model_path=model_path,
                    device=device,
                    epochs=100,
                    patience=10,
                    loss_mode=loss_mode,
                    metrics_token=metrics_token,
                    resume_epoch=checkpoint['epoch'],  # Resume from last checkpoint epoch
                )

if __name__ == "__main__":
    main()
