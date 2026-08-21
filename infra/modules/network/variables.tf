variable "name_prefix" {
  description = "Prefix used for resource names and Name tags (e.g. \"dmz-public-a\")"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "azs" {
  description = "Availability zones to spread subnets across"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets, one per AZ"
  type        = list(string)
}

variable "private_subnets" {
  description = "Private subnets to create, each with its own name and CIDR. AZ is assigned by position from var.azs (cycles if there are more subnets than AZs)."
  type = list(object({
    name = string
    cidr = string
  }))
}

variable "bastion_ssh_cidr" {
  description = "CIDR allowed to SSH into the bastion security group"
  type        = string
}
