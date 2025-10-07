"""Kubernetes manifest generator"""

from typing import Dict, Any, Optional, List
from loguru import logger
import yaml

from .base_generator import BaseGenerator


class KubernetesGenerator(BaseGenerator):
    """Generate Kubernetes manifests"""
    
    def __init__(self, output_dir: str = "./infrastructure/kubernetes"):
        """Initialize Kubernetes generator"""
        super().__init__(output_dir)
    
    def get_file_extension(self) -> str:
        """Get Kubernetes file extension"""
        return ".yaml"
    
    def generate(
        self,
        intent: Dict[str, Any],
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Kubernetes manifests
        
        Args:
            intent: Parsed user intent
            parameters: Extracted parameters
            context: Additional context
            
        Returns:
            Generated Kubernetes YAML
        """
        action = intent.get("action", "create")
        resources = intent.get("resources", [])
        
        logger.info(f"Generating Kubernetes manifests - action: {action}")
        
        manifests = []
        
        # Generate namespace
        manifests.append(self._generate_namespace(parameters))
        
        # Generate deployment
        if any(r in str(resources) for r in ["deployment", "pod", "container", "app"]):
            manifests.append(self._generate_deployment(parameters))
        
        # Generate service
        if any(r in str(resources) for r in ["service", "expose", "lb"]):
            manifests.append(self._generate_service(parameters))
        
        # Generate configmap if needed
        manifests.append(self._generate_configmap(parameters))
        
        # Generate ingress if needed
        if "ingress" in str(resources) or parameters.get("network", {}).get("load_balancer"):
            manifests.append(self._generate_ingress(parameters))
        
        # Combine all manifests
        yaml_docs = [m for m in manifests if m]
        return "\n---\n".join(yaml_docs)
    
    def _generate_namespace(self, parameters: Dict[str, Any]) -> str:
        """Generate namespace manifest"""
        general_params = parameters.get("general", {})
        namespace = general_params.get("environment", "default")
        
        manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": namespace,
                "labels": {
                    "name": namespace,
                    "managed-by": "autodevops"
                }
            }
        }
        
        return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    
    def _generate_deployment(self, parameters: Dict[str, Any]) -> str:
        """Generate deployment manifest"""
        general_params = parameters.get("general", {})
        compute_params = parameters.get("compute", {})
        scaling_params = parameters.get("scaling", {})
        network_params = parameters.get("network", {})
        
        app_name = general_params.get("name", "app")
        namespace = general_params.get("environment", "default")
        replicas = scaling_params.get("count", 3)
        
        # Container resources
        cpu = compute_params.get("cpu", 1)
        memory = compute_params.get("memory", "512Mi")
        
        # Ports
        ports = network_params.get("ports", [80])
        
        container_ports = []
        for port in ports:
            container_ports.append({
                "containerPort": port,
                "protocol": "TCP"
            })
        
        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"{app_name}-deployment",
                "namespace": namespace,
                "labels": {
                    "app": app_name,
                    "managed-by": "autodevops"
                }
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": app_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": app_name
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": app_name,
                            "image": f"{app_name}:latest",
                            "ports": container_ports,
                            "resources": {
                                "requests": {
                                    "cpu": f"{cpu}",
                                    "memory": memory
                                },
                                "limits": {
                                    "cpu": f"{cpu * 2}",
                                    "memory": memory
                                }
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": ports[0]
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/ready",
                                    "port": ports[0]
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5
                            },
                            "env": [{
                                "name": "ENVIRONMENT",
                                "value": namespace
                            }],
                            "envFrom": [{
                                "configMapRef": {
                                    "name": f"{app_name}-config"
                                }
                            }]
                        }]
                    }
                }
            }
        }
        
        # Add HPA if auto-scaling is enabled
        if scaling_params.get("auto_scaling"):
            hpa = self._generate_hpa(parameters)
            return yaml.dump(manifest, default_flow_style=False, sort_keys=False) + "\n---\n" + hpa
        
        return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    
    def _generate_hpa(self, parameters: Dict[str, Any]) -> str:
        """Generate Horizontal Pod Autoscaler"""
        general_params = parameters.get("general", {})
        scaling_params = parameters.get("scaling", {})
        
        app_name = general_params.get("name", "app")
        namespace = general_params.get("environment", "default")
        
        manifest = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{app_name}-hpa",
                "namespace": namespace
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": f"{app_name}-deployment"
                },
                "minReplicas": scaling_params.get("min_size", 2),
                "maxReplicas": scaling_params.get("max_size", 10),
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": 70
                            }
                        }
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": 80
                            }
                        }
                    }
                ]
            }
        }
        
        return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    
    def _generate_service(self, parameters: Dict[str, Any]) -> str:
        """Generate service manifest"""
        general_params = parameters.get("general", {})
        network_params = parameters.get("network", {})
        
        app_name = general_params.get("name", "app")
        namespace = general_params.get("environment", "default")
        ports = network_params.get("ports", [80])
        
        # Determine service type
        service_type = "LoadBalancer" if network_params.get("load_balancer") else "ClusterIP"
        
        service_ports = []
        for i, port in enumerate(ports):
            service_ports.append({
                "name": f"port-{i}",
                "port": port,
                "targetPort": port,
                "protocol": "TCP"
            })
        
        manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{app_name}-service",
                "namespace": namespace,
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "type": service_type,
                "selector": {
                    "app": app_name
                },
                "ports": service_ports
            }
        }
        
        return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    
    def _generate_configmap(self, parameters: Dict[str, Any]) -> str:
        """Generate ConfigMap manifest"""
        general_params = parameters.get("general", {})
        
        app_name = general_params.get("name", "app")
        namespace = general_params.get("environment", "default")
        
        manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{app_name}-config",
                "namespace": namespace
            },
            "data": {
                "APP_NAME": app_name,
                "LOG_LEVEL": "info",
                "ENVIRONMENT": namespace
            }
        }
        
        return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    
    def _generate_ingress(self, parameters: Dict[str, Any]) -> str:
        """Generate Ingress manifest"""
        general_params = parameters.get("general", {})
        network_params = parameters.get("network", {})
        security_params = parameters.get("security", {})
        
        app_name = general_params.get("name", "app")
        namespace = general_params.get("environment", "default")
        
        # Determine if SSL is enabled
        tls_enabled = security_params.get("ssl_enabled", False)
        
        manifest = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{app_name}-ingress",
                "namespace": namespace,
                "annotations": {
                    "kubernetes.io/ingress.class": "nginx"
                }
            },
            "spec": {
                "rules": [{
                    "host": f"{app_name}.example.com",
                    "http": {
                        "paths": [{
                            "path": "/",
                            "pathType": "Prefix",
                            "backend": {
                                "service": {
                                    "name": f"{app_name}-service",
                                    "port": {
                                        "number": 80
                                    }
                                }
                            }
                        }]
                    }
                }]
            }
        }
        
        if tls_enabled:
            manifest["spec"]["tls"] = [{
                "hosts": [f"{app_name}.example.com"],
                "secretName": f"{app_name}-tls"
            }]
        
        return yaml.dump(manifest, default_flow_style=False, sort_keys=False)
