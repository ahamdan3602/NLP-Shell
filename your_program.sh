set -e
exec pipenv run python3 -u -m app.main "$@"
