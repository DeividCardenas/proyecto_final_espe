"""Orquestador del pipeline Medallion completo: Bronze -> Silver -> Gold.

Uso:
    python -m app.services.etl.pipeline --since 2023-01-01
    python -m app.services.etl.pipeline --incremental
    python -m app.services.etl.pipeline --skip-download
    python -m app.services.etl.pipeline --incremental --train   # ETL + reentrenamiento

Con ``--train`` se regeneran la matriz de variables y ambos modelos ANTES de
exportar la Capa Gold, de modo que ``gold_grid_ml`` y ``gold_segment_risk`` nunca
quedan desfasados respecto a los datos recién cargados.
"""
from __future__ import annotations

import argparse
import logging

from app.services.etl import data_cleaner, soda_client, spatial_enrichment
from app.services.olap import duckdb_engine

logger = logging.getLogger("etl.pipeline")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pipeline ETL completo")
    parser.add_argument("--since", default="2023-01-01")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--buffer-meters", type=float, default=250.0)
    parser.add_argument("--lookback-days", type=int, default=soda_client.DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--train", action="store_true",
                        help="Reentrenar ambos modelos con los datos recién cargados antes de exportar Gold")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not args.skip_download:
        soda_client.ingest("aadt", since=None)
        for ds in ("permits", "crashes", "vehicles", "people"):
            soda_client.ingest(ds, since=args.since, incremental=args.incremental,
                               lookback_days=args.lookback_days)
    data_cleaner.main(["--verify-integrity"])
    spatial_enrichment.main(["--buffer-meters", str(args.buffer_meters)])
    if args.train:
        from app.ml import feature_engineering, segment_model, train

        feature_engineering.main([])
        train.main([])
        segment_model.main([])
    duckdb_engine.main(["--export"])
    logger.info("Pipeline Medallion completado")


if __name__ == "__main__":
    main()
