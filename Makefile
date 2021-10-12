.DEFAULT_GOAL := build
.PHONY := build install clean

build: setup.py src/pandelephant/_data/protos/pandelephant/models.proto
	python3 -m grpc_tools.protoc --python_out=src/ --proto_path=src/pandelephant/_data/protos pandelephant/models.proto
	# python3 setup.py generate_py_protobufs

install: build
	python3 setup.py install
# 	python3 setup.py bdist

clean:
	rm -f ./src/pandelephant/models_pb2.py
	python3 setup.py clean --all
	rm -rf ./*.egg-info
	rm -rf ./dist
# 	rm -rf ./build
