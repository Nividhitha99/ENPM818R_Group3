#!/bin/bash

cat <<EOF | kubectl apply -f -                                  
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers:
    - name: nginx
      image: nginx:latest
EOF

#  The pod creation will be blocked because of the kyverno's policies running successfully.