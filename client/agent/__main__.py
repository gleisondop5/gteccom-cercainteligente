import sys
import argparse
from . import Agent


def main(argsv=None):
    if argsv is None:
        argsv = sys.argv[1:]
        
    ap = argparse.ArgumentParser('python3 -m gteccom-cercainteligente.client.agent')
    ap.add_argument('--monitor', metavar='MONITOR_ADDRESS', required=True, help='Endere\u00E7o do servidor web (monitor server) para o qual o agente se reportar\u00E1.')
    ap.add_argument('--video', metavar='VIDEO_URI', required=True, help='V\u00EDdeo a ser processado pelo agente. Pode ser um endere\u00E7o RTSP ou um arquivo em disco.')
    ap.add_argument('--name', metavar='TAG_SLUG', required=True, help='Nome da c\u00E2mera monitorada pelo agente.')
    ap.add_argument('--dbhost', metavar='HOST_IP', required=True, help='Endere\u00E7o IP do servidor que hospeda a base de dados.')
    ap.add_argument('--dbport', metavar='HOST_PORT', required=False, default='5432', help='Porta do servidor que hospeda a base de dados (default = 5432).')
    ap.add_argument('--dbname', metavar='DATABASE', required=True, help='Nome da base de dados.')
    ap.add_argument('--dbuser', metavar='USERNAME', required=True, help='Nome do usu\u00E1rio com acesso \u00E0 base de dados.')
    ap.add_argument('--dbpwd', metavar='PASSWORD', required=True, help='Senha do usu\u00E1rio com acesso \u00E0 base de dados.')
    ap.add_argument('--nframe', metavar='NUM_THREADS', required=False, type=int, choices=range(1, 9), default=2, help='Quantidade de threads respons\u00E1veis pelo processamento dos quadros do v\u00EDdeo (default = 2).')
    ap.add_argument('--nstorage', metavar='NUM_THREADS', required=False, type=int, choices=range(1, 9), default=2, help='Quantidade de threads respons\u00E1veis pelo armazenamento das placas detectadas (default = 2).')
    
    args = vars(ap.parse_args(argsv))
        
    agent = Agent(args['name'])
    agent.run(
        monitor=args['monitor'],
        video_path=args['video'],
        database_host=args['dbhost'],
        database_port=args['dbport'],
        database_name=args['dbname'],
        database_user=args['dbuser'],
        database_password=args['dbpwd'],
        num_frame_workers=args['nframe'],
        num_local_storage_workers=args['nstorage'],
    )


if __name__ == '__main__':
    main()