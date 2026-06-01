from __future__ import annotations

import argparse
from pathlib import Path

from ui_auto_gen.pipeline import PipelineRunner
from ui_auto_gen.web.server import UiServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the automated UI image generation pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a pipeline job.")
    run_parser.add_argument("--config", required=True, help="Path to a job config JSON file.")
    run_parser.add_argument("--output-root", default=None, help="Directory where run artifacts will be written.")
    run_parser.add_argument("--run-id", default=None, help="Optional explicit run id.")
    run_parser.add_argument("--overwrite", action="store_true", help="Overwrite the run directory if it already exists.")

    serve_parser = subparsers.add_parser("serve", help="Run the local web UI.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host for the UI server.")
    serve_parser.add_argument("--port", type=int, default=8765, help="Port for the UI server.")
    serve_parser.add_argument("--output-root", default=None, help="Directory where run artifacts will be written.")

    args = parser.parse_args()

    if args.command == "run":
        output_root = Path(args.output_root).resolve() if args.output_root else None
        runner = PipelineRunner(output_root=output_root)
        context, results = runner.run(
            config_path=Path(args.config),
            run_id=args.run_id,
            overwrite=args.overwrite,
        )
        print(f"Run completed: {context.run_id}")
        print(f"Run root: {context.run_root}")
        for result in results:
            print(f"- {result.stage}: {result.status}")
        export_result = results[-1]
        summary = export_result.artifacts.get("summary")
        final_image = export_result.artifacts.get("final_image")
        if summary:
            print(f"Summary: {summary}")
        if final_image:
            print(f"Final image: {final_image}")
    elif args.command == "serve":
        output_root = Path(args.output_root).resolve() if args.output_root else None
        UiServer(host=args.host, port=args.port, output_root=output_root).serve()


if __name__ == "__main__":
    main()
