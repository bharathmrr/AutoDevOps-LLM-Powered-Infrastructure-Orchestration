"""Estimate infrastructure costs"""

from typing import Dict, Any, Optional, List
from loguru import logger
import re


class CostEstimator:
    """Estimate costs for Infrastructure-as-Code"""
    
    def __init__(self):
        """Initialize cost estimator"""
        self.pricing = self._load_pricing_data()
        logger.info("Cost estimator initialized")
    
    def _load_pricing_data(self) -> Dict[str, Any]:
        """Load pricing data for cloud resources"""
        # Simplified pricing data (actual prices vary by region and time)
        return {
            "aws": {
                "ec2": {
                    "t2.micro": 0.0116,
                    "t2.small": 0.023,
                    "t2.medium": 0.0464,
                    "t3.micro": 0.0104,
                    "t3.small": 0.0208,
                    "t3.medium": 0.0416,
                    "m5.large": 0.096,
                    "m5.xlarge": 0.192,
                },
                "rds": {
                    "db.t3.micro": 0.017,
                    "db.t3.small": 0.034,
                    "db.t3.medium": 0.068,
                },
                "s3": {
                    "storage_gb": 0.023,
                    "requests_per_1000": 0.0004,
                },
                "ebs": {
                    "gp3_gb": 0.08,
                    "gp2_gb": 0.10,
                },
                "alb": {
                    "hourly": 0.0225,
                    "lcu_hourly": 0.008,
                }
            },
            "azure": {
                "vm": {
                    "B1s": 0.0104,
                    "B2s": 0.0416,
                    "D2s_v3": 0.096,
                },
                "sql": {
                    "Basic": 0.0068,
                    "Standard_S0": 0.0203,
                }
            },
            "gcp": {
                "compute": {
                    "f1-micro": 0.0076,
                    "g1-small": 0.0257,
                    "n1-standard-1": 0.0475,
                }
            }
        }
    
    def estimate(
        self,
        code: str,
        iac_type: str,
        provider: Optional[str] = None,
        hours_per_month: int = 730
    ) -> Dict[str, Any]:
        """Estimate infrastructure costs
        
        Args:
            code: IaC code
            iac_type: Type of IaC
            provider: Cloud provider
            hours_per_month: Hours per month for calculation
            
        Returns:
            Cost estimate dictionary
        """
        logger.info(f"Estimating costs for {iac_type} on {provider}")
        
        if not provider:
            provider = self._detect_provider(code)
        
        costs = {
            "provider": provider,
            "currency": "USD",
            "breakdown": [],
            "monthly_total": 0.0,
            "yearly_total": 0.0,
            "warnings": []
        }
        
        if iac_type.lower() == "terraform":
            costs = self._estimate_terraform_costs(code, provider, hours_per_month)
        elif iac_type.lower() == "kubernetes":
            costs["warnings"].append("Kubernetes cost estimation requires cluster information")
        elif iac_type.lower() == "docker":
            costs["warnings"].append("Docker cost estimation depends on deployment platform")
        
        return costs
    
    def _detect_provider(self, code: str) -> str:
        """Detect cloud provider from code"""
        if 'aws_' in code or 'provider "aws"' in code:
            return "aws"
        elif 'azurerm_' in code or 'provider "azurerm"' in code:
            return "azure"
        elif 'google_' in code or 'provider "google"' in code:
            return "gcp"
        return "unknown"
    
    def _estimate_terraform_costs(
        self,
        code: str,
        provider: str,
        hours_per_month: int
    ) -> Dict[str, Any]:
        """Estimate Terraform infrastructure costs"""
        costs = {
            "provider": provider,
            "currency": "USD",
            "breakdown": [],
            "monthly_total": 0.0,
            "yearly_total": 0.0,
            "warnings": []
        }
        
        if provider == "aws":
            # Estimate EC2 costs
            ec2_costs = self._estimate_ec2_costs(code, hours_per_month)
            costs["breakdown"].extend(ec2_costs)
            
            # Estimate RDS costs
            rds_costs = self._estimate_rds_costs(code, hours_per_month)
            costs["breakdown"].extend(rds_costs)
            
            # Estimate S3 costs
            s3_costs = self._estimate_s3_costs(code)
            costs["breakdown"].extend(s3_costs)
            
            # Estimate ALB costs
            alb_costs = self._estimate_alb_costs(code, hours_per_month)
            costs["breakdown"].extend(alb_costs)
        
        # Calculate totals
        costs["monthly_total"] = sum(item["monthly_cost"] for item in costs["breakdown"])
        costs["yearly_total"] = costs["monthly_total"] * 12
        
        # Add warnings
        if costs["monthly_total"] > 1000:
            costs["warnings"].append("Estimated monthly cost exceeds $1,000")
        
        if costs["monthly_total"] == 0:
            costs["warnings"].append("Unable to estimate costs - insufficient information")
        
        return costs
    
    def _estimate_ec2_costs(self, code: str, hours_per_month: int) -> List[Dict[str, Any]]:
        """Estimate EC2 instance costs"""
        costs = []
        
        # Find EC2 instances
        instance_pattern = r'resource\s+"aws_instance"\s+"(\w+)".*?instance_type\s*=\s*"([^"]+)"'
        matches = re.finditer(instance_pattern, code, re.DOTALL)
        
        for match in matches:
            resource_name = match.group(1)
            instance_type = match.group(2)
            
            # Get pricing
            hourly_rate = self.pricing["aws"]["ec2"].get(instance_type, 0.0)
            
            if hourly_rate > 0:
                monthly_cost = hourly_rate * hours_per_month
                costs.append({
                    "resource_type": "EC2 Instance",
                    "resource_name": resource_name,
                    "details": f"Instance type: {instance_type}",
                    "hourly_cost": hourly_rate,
                    "monthly_cost": monthly_cost,
                    "yearly_cost": monthly_cost * 12
                })
            else:
                costs.append({
                    "resource_type": "EC2 Instance",
                    "resource_name": resource_name,
                    "details": f"Instance type: {instance_type} (pricing not available)",
                    "hourly_cost": 0.0,
                    "monthly_cost": 0.0,
                    "yearly_cost": 0.0
                })
        
        # Check for Auto Scaling Groups
        asg_pattern = r'resource\s+"aws_autoscaling_group".*?min_size\s*=\s*(\d+).*?max_size\s*=\s*(\d+)'
        asg_matches = re.finditer(asg_pattern, code, re.DOTALL)
        
        for match in asg_matches:
            min_size = int(match.group(1))
            max_size = int(match.group(2))
            avg_size = (min_size + max_size) / 2
            
            # Estimate based on average size (need instance type from launch template)
            costs.append({
                "resource_type": "Auto Scaling Group",
                "resource_name": "asg",
                "details": f"Estimated {avg_size} instances",
                "hourly_cost": 0.0,
                "monthly_cost": 0.0,
                "yearly_cost": 0.0,
                "note": "Actual cost depends on instance type and scaling behavior"
            })
        
        return costs
    
    def _estimate_rds_costs(self, code: str, hours_per_month: int) -> List[Dict[str, Any]]:
        """Estimate RDS database costs"""
        costs = []
        
        # Find RDS instances
        rds_pattern = r'resource\s+"aws_db_instance"\s+"(\w+)".*?instance_class\s*=\s*"([^"]+)"'
        matches = re.finditer(rds_pattern, code, re.DOTALL)
        
        for match in matches:
            resource_name = match.group(1)
            instance_class = match.group(2)
            
            # Get pricing
            hourly_rate = self.pricing["aws"]["rds"].get(instance_class, 0.0)
            
            # Check for Multi-AZ
            multi_az_match = re.search(r'multi_az\s*=\s*true', code)
            multiplier = 2 if multi_az_match else 1
            
            if hourly_rate > 0:
                monthly_cost = hourly_rate * hours_per_month * multiplier
                costs.append({
                    "resource_type": "RDS Instance",
                    "resource_name": resource_name,
                    "details": f"Instance class: {instance_class}, Multi-AZ: {multi_az_match is not None}",
                    "hourly_cost": hourly_rate * multiplier,
                    "monthly_cost": monthly_cost,
                    "yearly_cost": monthly_cost * 12
                })
        
        return costs
    
    def _estimate_s3_costs(self, code: str) -> List[Dict[str, Any]]:
        """Estimate S3 storage costs"""
        costs = []
        
        # Find S3 buckets
        s3_pattern = r'resource\s+"aws_s3_bucket"\s+"(\w+)"'
        matches = re.finditer(s3_pattern, code)
        
        for match in matches:
            resource_name = match.group(1)
            
            # S3 costs are usage-based, provide estimate for 100GB
            estimated_gb = 100
            storage_cost = estimated_gb * self.pricing["aws"]["s3"]["storage_gb"]
            
            costs.append({
                "resource_type": "S3 Bucket",
                "resource_name": resource_name,
                "details": f"Estimated {estimated_gb}GB storage",
                "hourly_cost": 0.0,
                "monthly_cost": storage_cost,
                "yearly_cost": storage_cost * 12,
                "note": "Actual cost depends on storage usage and requests"
            })
        
        return costs
    
    def _estimate_alb_costs(self, code: str, hours_per_month: int) -> List[Dict[str, Any]]:
        """Estimate Application Load Balancer costs"""
        costs = []
        
        # Find ALBs
        alb_pattern = r'resource\s+"aws_lb"\s+"(\w+)"'
        matches = re.finditer(alb_pattern, code)
        
        for match in matches:
            resource_name = match.group(1)
            
            hourly_rate = self.pricing["aws"]["alb"]["hourly"]
            lcu_rate = self.pricing["aws"]["alb"]["lcu_hourly"]
            
            # Estimate 1 LCU on average
            total_hourly = hourly_rate + lcu_rate
            monthly_cost = total_hourly * hours_per_month
            
            costs.append({
                "resource_type": "Application Load Balancer",
                "resource_name": resource_name,
                "details": "Estimated 1 LCU average",
                "hourly_cost": total_hourly,
                "monthly_cost": monthly_cost,
                "yearly_cost": monthly_cost * 12,
                "note": "LCU costs vary based on traffic"
            })
        
        return costs
    
    def compare_alternatives(
        self,
        code: str,
        iac_type: str,
        provider: str
    ) -> List[Dict[str, Any]]:
        """Suggest cost-saving alternatives
        
        Args:
            code: IaC code
            iac_type: Type of IaC
            provider: Cloud provider
            
        Returns:
            List of cost-saving suggestions
        """
        suggestions = []
        
        # Check for oversized instances
        if 'm5.xlarge' in code or 'm5.2xlarge' in code:
            suggestions.append({
                "type": "instance_sizing",
                "description": "Consider using smaller instance types if workload permits",
                "potential_savings": "30-50%"
            })
        
        # Check for reserved instances opportunity
        if 'aws_instance' in code:
            suggestions.append({
                "type": "pricing_model",
                "description": "Consider Reserved Instances or Savings Plans for predictable workloads",
                "potential_savings": "40-60%"
            })
        
        # Check for spot instances opportunity
        if 'aws_autoscaling_group' in code:
            suggestions.append({
                "type": "spot_instances",
                "description": "Consider using Spot Instances for fault-tolerant workloads",
                "potential_savings": "70-90%"
            })
        
        return suggestions
