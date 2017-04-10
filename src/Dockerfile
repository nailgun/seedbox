FROM python:3.6.1-onbuild

ENV PYTHONPATH="/urs/src/app:${PYTHONPATH}"

ENTRYPOINT ["python", "seedbox/__main__.py"]
CMD ["runserver"]

