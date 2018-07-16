# Ames housing value prediction using XGBoost on Kubeflow

In this example we will demonstrate how to use Kubeflow with XGBoost using the [Kaggle Ames Housing Prices prediction](https://www.kaggle.com/c/house-prices-advanced-regression-techniques/). We will do a detailed
walk-through of how to implement, train and serve the model. You will be able to run the exact same workload on-prem and/or on any cloud provider. We will be using [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/) to show how the end-to-end workflow runs on [Google Cloud Platform](https://cloud.google.com/). 

# Pre-requisites

As a part of running this setup on Google Cloud Platform, make sure you have enabled the [Google
Kubernetes Engine](https://cloud.google.com/kubernetes-engine/). In addition to that you will need to install
[Docker](https://docs.docker.com/install/) and [gcloud](https://cloud.google.com/sdk/downloads). Note that this setup can run on-prem and on any cloud provider, but here we will demonstrate GCP cloud option. 

# Steps
 * [Kubeflow Setup](#kubeflow-setup)
 * [Data Preparation](#data-preparation)
 * [Dockerfile](#dockerfile)
 * [Model Training](#model-training)
 * [Model Export](#model-export)
 * [Model Serving Locally](#model-serving)
 * [Deploying Model to Kubernetes Cluster](#deploying-the-model-to-kubernetes-cluster)

## Kubeflow Setup
In this part you will setup Kubeflow on an existing Kubernetes cluster. Checkout the Kubeflow [setup guide](https://github.com/kubeflow/kubeflow#setup).  

### Requirements

 * ksonnet
 * Kubernetes
 * minikube
 * hyperkit (vm-driver)

## Data Preparation
You can download the dataset from the [Kaggle competition](https://www.kaggle.com/c/house-prices-advanced-regression-techniques/data). In order to make it convenient we have uploaded the dataset on Github here [xgboost/ames_dataset](ames_dataset). 

## Dockerfile
We have attached a Dockerfile with this repo which you can use to create a
docker image. We have also uploaded the image to gcr.io, which you can use to
directly download the image.

```
IMAGE_NAME=ames-housing
VERSION=v1
```

Use `gcloud` command to get the GCP project

```
PROJECT_ID=`gcloud config get-value project`
```

Let's create a docker image from our Dockerfile

```
docker build -t gcr.io/$PROJECT_ID/${IMAGE_NAME}:${VERSION} .
```

Once the above command is successful you should be able to see the docker
images on your local machine `docker images`. Next we will upload the image to
[Google Container Registry](https://cloud.google.com/container-registry/)

```
gcloud auth configure-docker
docker push gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${VERSION}
```

## Model Training

Once you have performed `docker build` you should be able to see the images by running `docker images`. Run the training by issuing the following command 

```
IMAGE=gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${VERSION}
docker run -v /tmp/ames/:/model/ames -it $IMAGE --train-input examples/xgboost/ames_dataset/train.csv \
                                                --model-file /model/ames/housing.dat \
                                                --learning-rate 0.1 \
                                                --n-estimators 30000 \
                                                --early-stopping-rounds 50
```

In the above command we have mounted the container filesystem `/model/ames` to the host filesystem `/tmp/ames` so that the model is available on localhost. Check the local host filesystem for the trained XGBoost model

```
ls -lh /tmp/ames/housing.dat
```

### Run the model training on GKE
In this section we will run the above docker container on a [Google Kubernetes Engine](gke). There are two steps to eprform the training

 * Create a GKE cluster
   Follow the [instructions](https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-cluster) to create a GKE cluster
   
   ```
   CLUSTER_NAME=xgboost-kf
   COMPUTE_ZONE=us-central1-a
   gcloud container clusters create $CLUSTER_NAME --zone $COMPUTE_ZONE --num-nodes 1
   ```
   
 * Create a Persistent Volume by following the instructions [here](https://kubernetes.io/docs/tasks/configure-pod-container/configure-persistent-volume-storage/). You will need to run the following `kubectl create` commands in order to get the `claim` attached to the `pod`.
 
 ```
 kubectl create -f py-volume.yaml
 kubectl create -f py-claim.yaml
 ```

 
 * Run docker container on GKE
   Use the `kubectl` command to run the image on GKE
   
   ```
   kubectl create -f py-pod.yaml
   ```
   
   Once the above command finishes you will have an XGBoost model at `/mnt/xgboost/housing.dat`
   
   ```
   [202]	validation_0-rmse:30068.2
[203]	validation_0-rmse:30118.9
[204]	validation_0-rmse:30117.3
[205]	validation_0-rmse:30105.4
Stopping. Best iteration:
[165]	validation_0-rmse:30021

Best RMSE on eval: 30020.96 with 166 rounds

MAE on test: 16991.32
Model export success /mnt/xgboost/housing.dat
   ```

## Model Export
The model is exported at location `/tmp/ames/housing.dat`. We will use [Seldon Core](https://github.com/SeldonIO/seldon-core/) to serve the model asset. In order to make the model servable we have created `xgboost/seldon_serve` with the following assets

 * `HousingServe.py`
 * `housing.dat`
 * `requirements.txt`

## Model Serving
We are going to use [seldon-core](https://github.com/SeldonIO/seldon-core/) to serve the model. [HousingServe.py](seldon_serve/HousingServe.py) contains the code to serve the model. Run the following command to create a microservice 

```
docker run -v $(pwd):/seldon_serve seldonio/core-python-wrapper:0.7 /seldon_serve HousingServe 0.1 seldonio
```

Let's build the seldon-core microservice image. You can find seldon core model wrapping details [here](https://github.com/SeldonIO/seldon-core/blob/master/docs/wrappers/python.md).

```
cd build
./build_image.sh
```

You should see the docker image locally `seldonio/housingserve` which can be run locally to serve the model. 

```
docker run -p 5000:5000 seldonio/housingserve:0.1
```

Now you are ready to send requests on `localhost:5000`

```
curl -H "Content-Type: application/x-www-form-urlencoded" -d 'json={"data":{"tensor":{"shape":[1,37],"values":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37]}}}' http://localhost:5000/predict
```

```
{
  "data": {
    "names": [
      "t:0", 
      "t:1"
    ], 
    "tensor": {
      "shape": [
        1, 
        2
      ], 
      "values": [
        97522.359375, 
        97522.359375
      ]
    }
  }
}
```

### Model deployment on local Kubernetes Cluster (Minikube)
One of the amazing features of Kubernetes is that you can run it anywhere i.e., local, on-prem and cloud. We will show you how to run your code on local Kubernetes cluster created using minikube and the exact workflow will work on the cloud. 

Start a local Kubernetes cluster using minikube and specify a `--vm-driver` and checkout the cluster configuration in UI.

```
minikube start --vm-driver=hyperkit
minikube dashboard #opens a dashboard local Kubernetes UI
```

Deploy Seldon core to your minikube Kubernetes cluster by following the instructions [here](https://github.com/kubeflow/examples/blob/fb2fb26f710f7c03996f08d81607f5ebf7d5af09/github_issue_summarization/serving_the_model.md#deploy-seldon-core). Once everything is successful you can verify it using `kubectl get pods -n${NAMESPACE}`.

```
NAME                                      READY     STATUS    RESTARTS   AGE
ambassador-849fb9c8c5-5kx6l               2/2       Running   0          16m
ambassador-849fb9c8c5-pww4j               2/2       Running   0          16m
ambassador-849fb9c8c5-zn6gl               2/2       Running   0          16m
redis-75c969d887-fjqt8                    1/1       Running   0          30s
seldon-cluster-manager-6c78b7d6c9-6qhtg   1/1       Running   0          30s
spartakus-volunteer-66cc8ccd5b-9f8tw      1/1       Running   0          16m
tf-hub-0                                  1/1       Running   0          16m
tf-job-dashboard-7b57c549c8-bfpp8         1/1       Running   0          16m
tf-job-operator-594d8c7ddd-lqn8r          1/1       Running   0          16m
```
Depoloy the XGBoost model

```
ks generate seldon-serve-simple xgboost-ames   \
                                --name=xgboost-ames   \
                                --image=seldonio/housingserve:0.1   \
                                --namespace=${NAMESPACE}   \
                                --replicas=2
                                
ks apply ${KF_ENV} -c xgboost-ames
```
