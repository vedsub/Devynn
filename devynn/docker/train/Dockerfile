FROM pytorch/pytorch:2.2.0-cuda11.8-cudnn8-runtime

WORKDIR /opt/ml/code

COPY docker/train/requirements-train.txt .

RUN pip install -r requirements-train.txt --no-cache-dir

COPY docker/train/train.py .

ENTRYPOINT ["python", "train.py"]
