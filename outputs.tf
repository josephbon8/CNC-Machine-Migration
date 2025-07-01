#X.509 cert for mqtt tls handshake
output "cert_pem"{
    value = aws_iot_certificate.cert.certificate_pem
    sensitive = true
}


output "private_key" {
  value = aws_iot_certificate.cert.private_key 
  sensitive = true

}

output "public_key" {
  value = aws_iot_certificate.cert.public_key
  sensitive = true
}


