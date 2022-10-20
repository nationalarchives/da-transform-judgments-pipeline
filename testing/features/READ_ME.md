# notes to run features and unit tests (will soon move lambda to own repo and so structure /running details tbc )

## To run features
install behave with:       `pip install behave`
check installation with:   `behave --version`
in `testing` directory:
 `export PYTHONPATH=../lambda_functions/tre-bagit-to-dri-sip`
  run with `behave` 

## To run unit tests:
in `testing/tre_bagit_to_dri_sip`
 `export PYTHONPATH=../../lambda_functions/tre-bagit-to-dri-sip`
  run with `python -m unittest discover`