import sys
import os
import psutil
import argparse
import time
import json


def main():

    parser = argparse.ArgumentParser(description='training args.')

    parser.add_argument('--nproc_per_node', type=int, default=4, help='number of gpu used in distributed')
    parser.add_argument('--master_port', type=int, default=12233, help='master port used in distributed')
    parser.add_argument('--config_file', type=str, default='', help='path to training config')
    parser.add_argument('--resume_checkpoint', type=str, default='',
                        help='(optional) resume checkpoint to use. '
                             'in this case, config_file will automatically be found.')

    parser.add_argument('--notes', type=str, default='-', help='as training notes or specifical args')
    parser.add_argument('--app', type=str, default='', help='other input args')

    args = parser.parse_args()

    # set working dir to the upper folder
    abspath = os.path.abspath(__file__)
    dirname = os.path.dirname(abspath)
    dirname = os.path.dirname(dirname)
    sys.path.append(dirname)  # Assure upper folder import
    os.chdir(dirname)

    import config

    if args.resume_checkpoint:   # TODO : RESUME 있을때 없을때 다 잘되는가 확인하기
        resume_checkpoint = args.resume_checkpoint
        if not os.path.isfile(resume_checkpoint):
            raise argparse.ArgumentTypeError("--resume_checkpoint does not exist: {}".format(resume_checkpoint))
        elif args.config_file:
            raise argparse.ArgumentTypeError("You should specify only one of --config_file or --resume_checkpoint.")
        config_file = os.path.join(os.path.dirname(resume_checkpoint), 'training_args.json')
    else:
        resume_checkpoint = None
        config_file = args.config_file
        if not config_file:
            raise argparse.ArgumentTypeError("You should specify either --config_file or --resume_checkpoint.")
    if not os.path.isfile(config_file):
        raise argparse.ArgumentTypeError("--config_file does not exist: {}".format(config_file))

    with open(config_file) as fp:
        train_py_configs = json.load(fp)

    if resume_checkpoint is not None:
        train_py_configs['resume_checkpoint'] = resume_checkpoint
        if 'checkpoint_path' in train_py_configs:
            train_py_configs.pop('checkpoint_path')
    args.__dict__.update(config.load_dict_config(train_py_configs))

    from importlib.util import find_spec
    if find_spec('torch.distributed.run') is not None:
        distributed_run = 'torch.distributed.run'
        use_env = ''
    else:
        distributed_run = 'torch.distributed.launch'
        use_env = '--use_env'

    folder_name = "diffusion_models/"

    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)

    model_file = f"diffuseq_{args.dataset}_h{args.hidden_dim}_lr{args.lr}" \
                 f"_t{args.diffusion_steps}_{args.noise_schedule}_{args.schedule_sampler}" \
                 f"_seed{args.seed}"
    if args.notes:
        args.notes += time.strftime("%Y%m%d-%H:%M:%S")
        model_file = model_file + f'_{args.notes}'
    model_file = os.path.join(folder_name, model_file)

    if not os.path.isdir(model_file):
        os.mkdir(model_file)

    os.environ.setdefault("OMP_NUM_THREADS", str(psutil.cpu_count(logical=False) // int(args.nproc_per_node)))

    commandline = f"OMP_NUM_THREADS={os.environ['OMP_NUM_THREADS']} OPENAI_LOGDIR={model_file} " \
                  f"python -m {distributed_run} " \
                  f"--nproc_per_node={args.nproc_per_node} --master_port={args.master_port} {use_env} " \
                  f"train.py " \
                  f"--checkpoint_path {model_file} "
    for k, v in train_py_configs.items():
        if isinstance(v, str) and not v:
            continue
        if isinstance(v, bool):
            v = 'y' if v else 'n'
        commandline += f"--{k} {v} "
    commandline += args.app

    with open(os.path.join(model_file, 'saved_bash.sh'), 'w') as f:
        print(commandline, file=f)

    print(commandline)
    os.system(commandline)


if __name__ == '__main__':
    main()
