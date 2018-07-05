import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import Imputer
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error

def read_input(file_name, test_size=0.25):
    """Read input data and split it into train and test."""
    data = pd.read_csv(file_name[0])
    data.dropna(axis=0, subset=['SalePrice'], inplace=True)

    y = data.SalePrice
    X = data.drop(['SalePrice'], axis=1).select_dtypes(exclude=['object'])

    train_X, test_X, train_y, test_y = train_test_split(X.values,
                                                        y.values,
                                                        test_size=test_size)
    
    imputer = Imputer()
    train_X = imputer.fit_transform(train_X)
    test_X = imputer.transform(test_X)

    return (train_X, train_y), (test_X, test_y)

def train_model(train_X,
                train_y,
                test_X,
                test_y,
                n_estimators,
                learning_rate):
    """Train the model using XGBRegressor."""
    model = XGBRegressor(n_estimators=n_estimators,
                         learning_rate=learning_rate)

    model.fit(train_X,
              train_y,
              early_stopping_rounds=40,
              eval_set=[(test_X, test_y)])

    print("Best RMSE on eval: {:.2f} with {} rounds".format(
                 model.best_score,
                 model.best_iteration+1))
    return model

def eval_model(model, test_X, test_y):
    """Evaluate the model performance."""
    predictions = model.predict(test_X)
    print
    print("MAE on test: {:.2f}".format(mean_absolute_error(predictions, test_y)))

def save_model(model, model_file):
    """Save XGBoost model for serving."""
    joblib.dump(model, model_file)

def main(args):
    (train_X, train_y), (test_X, test_y) = read_input(args.train_input)
    model = train_model(train_X,
                        train_y,
                        test_X,
                        test_y,
                        args.n_estimators,
                        args.learning_rate)

    eval_model(model, test_X, test_y)
    save_model(model, args.model_file)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '--train-input',
            help="Input training file",
            nargs='+',
            required=True
    )
    parser.add_argument(
            '--n-estimators',
            help='Number of trees in the model',
            type=int,
            default=1000
    )
    parser.add_argument(
            '--learning-rate',
            help='Learning rate for the model',
            default=0.1
    )
    parser.add_argument(
            '--model-file',
            help='Model file location for XGBoost',
            required=True
    )
    parser.add_argument(
            '--test-size',
            help='Fraction of training data to be reserved for test',
            default=0.25
    )
    parser.add_argument(
            '--early-stopping-rounds',
            help='XGBoost argument for stopping early',
            default=50
    )

    args = parser.parse_args()
    main(args)
