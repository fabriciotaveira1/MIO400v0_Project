from core.commbox_client import CommboxClient
from core.opcodes.output import build_output_command

client = CommboxClient("192.168.26.228", 5000)

data = build_output_command(
    component_addr=1,
    action=1
)

response = client.send(1, data)

print(response)