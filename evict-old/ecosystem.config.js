module.exports = {
    apps: [
        {
            name: 'evict-cluster-0',
            script: 'python3.12',
            args: ['bot.py', '0'],
            interpreter: '/root/evict/.venv/bin/python3',
            cwd: '/root/evict',
            env: {
                CLUSTER_ID: '0',
                PYTHONPATH: '/root/evict'
            }
        },
        {
            name: 'evict-cluster-1',
            script: 'python3.12',
            args: ['bot.py', '1'],
            interpreter: '/root/evict/.venv/bin/python3',
            cwd: '/root/evict',
            env: {
                CLUSTER_ID: '1',
                PYTHONPATH: '/root/evict'
            }
        }
    ]
};