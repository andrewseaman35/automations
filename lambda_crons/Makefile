PACKAGE_DIR = packages

deploy_venv: requirements.txt
	virtualenv deploy_venv --python=python3 --no-site-packages
	deploy_venv/bin/pip install -r requirements.txt

_package_dir:
	mkdir -p $(PACKAGE_DIR)
	mkdir -p $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)

_package: _package_dir deploy_venv
	deploy_venv/bin/pip install -r $(LAMBDA_FUNCTION)/requirements.txt -t $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cp -r $(LAMBDA_FUNCTION)/* $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cp base/lambda_handler_base.py $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cd $(PACKAGE_DIR)/$(LAMBDA_FUNCTION) && zip -r ../$(LAMBDA_FUNCTION).zip *

clean:
	rm -rf $(PACKAGE_DIR)

.PHONY: _package _package_dir
