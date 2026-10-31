
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
 }

    post {
        always {
            echo 'HemoCare CI pipeline execution completed.'
        }
    }
}
