

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Check Python') {
            steps {
                bat '''
                "C:\\Users\\ritik\\AppData\\Local\\Programs\\Python\\Python314\\python.exe" --version
                '''
            }
        }

        stage('Create CI Environment') {
            steps {
                bat '''
                "C:\\Users\\ritik\\AppData\\Local\\Programs\\Python\\Python314\\python.exe" -m venv "%WORKSPACE%\\.venv"
                "%WORKSPACE%\\.venv\\Scripts\\python.exe" -m pip install --upgrade pip
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                dir('HemoCare') {
                    bat '''
icacls "%SSH_KEY%" /inheritance:r
icacls "%SSH_KEY%" /grant:r SYSTEM:F
                    "%WORKSPACE%\\.venv\\Scripts\\python.exe" -m pip install -r requirements-ci.txt
                    '''
                }
            }
        }

        stage('Run Tests') {
            steps {
                dir('HemoCare') {
                    withEnv([
                        "HEMOCARE_DB_NAME=${env.WORKSPACE}\\ci-test-${env.BUILD_NUMBER}.db",
                        "SECRET_KEY=jenkins-ci-only-not-production"
                    ]) {
                        bat '''
                        "%WORKSPACE%\\.venv\\Scripts\\python.exe" -m unittest -v test_app
                        '''
                    }
                }
            }
        }

        stage('Deploy to Stage') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'hemocare-stage-ssh',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    bat '''
                    echo Checking SSH and SCP availability...
                    where ssh
                    where scp

                    echo Transferring Stage deployment script...

                    scp -i "%SSH_KEY%" -o StrictHostKeyChecking=accept-new -o BatchMode=yes scripts/deploy-stage.sh "%SSH_USER%@54.252.222.146:/tmp/hemocare-deploy-stage.sh"

                    if errorlevel 1 exit /b 1

                    echo Executing Stage deployment...

                    ssh -i "%SSH_KEY%" -o StrictHostKeyChecking=accept-new -o BatchMode=yes "%SSH_USER%@54.252.222.146" "chmod 700 /tmp/hemocare-deploy-stage.sh && sed -i 's/\\r$//' /tmp/hemocare-deploy-stage.sh && bash /tmp/hemocare-deploy-stage.sh"

                    if errorlevel 1 exit /b 1

                    echo Stage deployment completed.
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'HemoCare CI and Stage deployment completed successfully.'
        }

        failure {
            echo 'HemoCare pipeline failed. Check the stage logs.'
        }

        always {
            echo 'HemoCare pipeline execution completed.'
        }
    }
}
