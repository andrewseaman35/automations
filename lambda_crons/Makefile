PACKAGE_DIR = packages

deploy_venv: requirements.txt
	virtualenv deploy_venv --python=python3
	deploy_venv/bin/pip install -r requirements.txt

install_venv:
	virtualenv install_venv --python=python3

_package_dir:
	mkdir -p $(PACKAGE_DIR)
	mkdir -p $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)

_package: _package_dir install_venv
	install_venv/bin/pip install -r $(LAMBDA_FUNCTION)/requirements.txt -t $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cp -r $(LAMBDA_FUNCTION)/* $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cp -r base $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cd $(PACKAGE_DIR)/$(LAMBDA_FUNCTION) && zip -r ../$(LAMBDA_FUNCTION).zip *

clean:
	rm -rf $(PACKAGE_DIR)

.PHONY: _package _package_dir
