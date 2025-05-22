module.exports = {
  apps: [{
    name: 'vesta',
    script: '/root/vesta/run.sh',
    interpreter: '/bin/bash',
    cwd: '/root/vesta',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/root/vesta'
    }
  }]
};