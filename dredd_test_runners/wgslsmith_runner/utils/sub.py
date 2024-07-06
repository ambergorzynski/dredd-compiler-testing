import subprocess

if __name__=="__main__":

    '''
    ls = subprocess.Popen(['ls'],stdout=subprocess.PIPE)
    grep = subprocess.Popen(['grep', 'mutant'],stdin=ls.stdout,stdout=subprocess.PIPE,encoding='utf-8')
    output,error=grep.communicate()
    '''


    nvidia_smi = subprocess.Popen(
            ["nvidia-smi"], 
            stdout=subprocess.PIPE
            )
    processes = subprocess.Popen(
            ["grep","wgslsmith"], 
            stdin=nvidia_smi.stdout, 
            stdout=subprocess.PIPE, 
            text=True
            )

    output1, error1 = processes.communicate()
    print(f'return code: {processes.returncode}')

    if processes.returncode == 0:
            
        print('killing!')
        nvidia_smi = subprocess.Popen(
                ["nvidia-smi"], 
                stdout=subprocess.PIPE
                )
        processes = subprocess.Popen(
                ["grep","wgslsmith"], 
                stdin=nvidia_smi.stdout, 
                stdout=subprocess.PIPE, 
                text=True
                )
        pid_to_kill = subprocess.Popen(
                ["awk","{ print $5 }"],
                stdin=processes.stdout,
                stdout=subprocess.PIPE,
                text=True
                )
        kill = subprocess.Popen(
                ["xargs", "-n1", "kill", "-9"],
                stdin=pid_to_kill.stdout,
                stdout=subprocess.PIPE,
                text=True
                )
        output, error = kill.communicate()
