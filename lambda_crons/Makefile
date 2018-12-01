PACKAGE_DIR = packages

venv:
	virtualenv venv --python=python3 --no-site-packages

package_dir:
	mkdir -p $(PACKAGE_DIR)
	mkdir -p $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)

package: package_dir venv
	venv/bin/pip install -r $(LAMBDA_FUNCTION)/requirements.txt -t $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cp -r $(LAMBDA_FUNCTION)/* $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cp base/lambda_handler_base.py $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)
	cd $(PACKAGE_DIR)/$(LAMBDA_FUNCTION) && zip -r ../$(LAMBDA_FUNCTION).zip *

clean:
	rm -rf ./venv/
	rm -rf $(PACKAGE_DIR)

