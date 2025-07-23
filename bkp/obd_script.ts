hexadecimal_original = 40408600043231384c534142323032353030303030320000001001508e7a681e997a68fea3190069a000002b480000410100020400033729441100831c01120719123923c83bee042cf84d0923024a06dc42342e332e392e325f42524c20323032342d30312d323520303100442d3231384c53412d4220204844432d333656000000d88b0d0a

4040 //  Cabeçalho do pacote

8600 //  Tamanho do pacote

04 // versão do protocolo

3231384c53414232303235303030303032000000 //  ID do dispositivo

1001 //  Protocolo ID

508e7a68 // last_accon_time

1e997a68 // UTC-Time

fea31900 // Total de quilometragem do veículo

69a00000 // Total da quilometragem da viagem atual

2b480000 // Total de combustível consumido

4101 // Current_fuel

00020400 // Estado do motor

03 37 29 44 // (necessário converter para hexadecimal)

1100831c01120719 // Reservado,11 ISO9141 (passenger)

                    00 // voltagem do veículo

                    83 // frequencia da rede

                    31 // hardware code��refer to hardware code table.5--213GD,7---SIM800L��

                    c0 // cellular signal strength��

                    11 // BER of cellular communication��

                    20719 // (necessário converter para hexadecimal)

12 // gps_count

3923c8 // Data

3bee04 // Hora

2cf84d09 // latitude

23024a06 // longitude

dc42 // velocidade do veículo

342e // direção do veículo

332e392e325f42524c20323032342d30312d3235 // versão do sistema

20303100442d3231384c53412d4220204844432d // versão do dispositivo

3336 // novo parametro

5600 //0056 alertas smsm

0000 // 0000 alerta telefone

d88b0d0a //  Dados do pacote