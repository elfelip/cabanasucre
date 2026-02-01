set -e
cd console_sucrier
poetry install
poetry build
poetry publish

cd ../bouillage
poetry install
poetry build
poetry publish