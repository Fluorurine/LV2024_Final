import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as path from "path";
import * as rds from "aws-cdk-lib/aws-rds";
import * as ssm from "aws-cdk-lib/aws-ssm";
import * as s3 from "aws-cdk-lib/aws-s3";
import { NetworkMode } from "aws-cdk-lib/aws-ecr-assets";

import { Vpc } from "./assistant-vpc";
import { AssistantApiConstruct } from "./assistant-api-gateway";
import { CognitoConstruct } from "./assistant-authorizer";
// import { SageMakerRdsAccessConstruct } from "./assistant-sagemaker-postgres-acess";
// import { SageMakerIAMPolicyConstruct } from "./assistant-sagemaker-iam-policy";
// import { SageMakerProcessor } from "./assistant-sagemaker-processor";

const AGENT_DB_NAME = "AgentSQLDBandVectorStore";

export class ServerlessLlmAssistantStack extends cdk.Stack {
	constructor(scope: Construct, id: string, props?: cdk.StackProps) {
		super(scope, id, props);

		// -----------------------------------------------------------------------
		// VPC Construct
		// Create subnets and VPC endpoints
		const vpc = new Vpc(this, "Vpc");

		// -----------------------------------------------------------------------
		// Create relevant SSM parameters
		const parameters = this.node.tryGetContext("parameters") || {
			bedrock_region: "us-east-1",
			llm_model_id: "anthropic.claude-3-haiku-20240307-v1:0",
		};

		const BEDROCK_REGION = parameters["bedrock_region"];
		const LLM_MODEL_ID = parameters["llm_model_id"];

		// Note: the SSM parameters for Bedrock region and endpoint are used
		// to setup a boto3 bedrock client for programmatic access to Bedrock APIs.

		// Add an SSM parameter for the Bedrock region.
		const ssm_bedrock_region_parameter = new ssm.StringParameter(
			this,
			"ssmBedrockRegionParameter",
			{
				parameterName: "/AgenticLLMAssistantWorkshop/bedrock_region",
				// This is the default region.
				// The user can update it in parameter store.
				stringValue: BEDROCK_REGION,
			}
		);

		// Add an SSM parameter for the llm model id.
		const ssm_llm_model_id_parameter = new ssm.StringParameter(
			this,
			"ssmLLMModelIDParameter",
			{
				parameterName: "/AgenticLLMAssistantWorkshop/llm_model_id",
				// This is the default region.
				// The user can update it in parameter store.
				stringValue: LLM_MODEL_ID,
			}
		);

		// -----------------------------------------------------------------------
		// Placeholder for Lab 4, step 2.2 - Put the database resource definition here.
		// Add an Amazon Aurora PostgreSQL database with PGvector for semantic search.
		// Create an Aurora PostgreSQL database to serve as the semantic search
		// engine using the pgvector extension https://github.com/pgvector/pgvector
		// https://aws.amazon.com/about-aws/whats-new/2023/07/amazon-aurora-postgresql-pgvector-vector-storage-similarity-search/

		// Add an Amazon Aurora PostgreSQL database with PGvector for semantic search.
		// Create an Aurora PostgreSQL database to serve as the semantic search
		// engine using the pgvector extension https://github.com/pgvector/pgvector
		// https://aws.amazon.com/about-aws/whats-new/2023/07/amazon-aurora-postgresql-pgvector-vector-storage-similarity-search/
		// const AgentDBSecret = rds.Credentials.fromGeneratedSecret("AgentDBAdmin");

		// const AgentDB = new rds.DatabaseCluster(this, "AgentDB", {
		//   engine: rds.DatabaseClusterEngine.auroraPostgres({
		//     // We use this specific db version because it comes with pgvector extension.
		//     version: rds.AuroraPostgresEngineVersion.VER_15_3,
		//   }),
		//   defaultDatabaseName: AGENT_DB_NAME,
		//   storageEncrypted: true,
		//   // Switch to cdk.RemovalPolicy.RETAIN when installing production
		//   // to avoid accidental data deletions.
		//   removalPolicy: cdk.RemovalPolicy.DESTROY,
		//   // We attach the credentials created above, to the database.
		//   credentials: AgentDBSecret,
		//   // Writer must be provided.
		//   writer: rds.ClusterInstance.serverlessV2("ServerlessInstanceWriter"),
		//   // Put the database in the vpc created above.
		//   vpc: vpc.vpc,
		//   // Put the database in the private subnet of the VPC.
		//   vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED }
		// });

		// Fix by Truong
		const AgentDBSecret = rds.Credentials.fromGeneratedSecret("AgentDBAdmin");

		// Define the RDS PostgreSQL instance
		const AgentDB = new rds.DatabaseInstance(this, "AgentDB", {
			engine: rds.DatabaseInstanceEngine.postgres({
				version: rds.PostgresEngineVersion.VER_16_3, // Specify PostgreSQL version 16.3
			}),
			databaseName: AGENT_DB_NAME,
			instanceType: ec2.InstanceType.of(
				ec2.InstanceClass.T3,
				ec2.InstanceSize.MICRO
			),
			vpc: vpc.vpc,
			credentials: AgentDBSecret, // Use the generated credentials
			vpcSubnets: {
				subnetType: ec2.SubnetType.PUBLIC, // Place the database in the private subnets
			},
			publiclyAccessible: true, // Make the database publicly accessible
			storageEncrypted: true, // Enable storage encryption
			allocatedStorage: 20, // Allocate 20 GB of storage
			removalPolicy: cdk.RemovalPolicy.DESTROY, // Destroy the database upon stack deletion (use RETAIN for production)
			deletionProtection: false, // Disable deletion protection (enable for production to prevent accidental deletion)
			multiAz: false, // Enable Multi-AZ for high availability
			autoMinorVersionUpgrade: false, // Enable automatic minor version upgrades
		});
		// End Fix by Truong
		// -----------------------------------------------------------------------
		// Lab 4. Step 4.1 - configure sagemaker access to the database.
		// Create a security group to allow access to the DB from a SageMaker processing job
		// which will be used to index embedding vectors.

		// const sagemaker_rds_access = new SageMakerRdsAccessConstruct(
		// 	this,
		// 	"SageMakerRdsAccess",
		// 	{
		// 		vpc: vpc.vpc,
		// 		rdsCluster: AgentDB,
		// 	}
		// );

		// Add a DynamoDB table to store chat history per session id.

		// When you see a need for it, consider configuring autoscaling to the table
		// https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_dynamodb-readme.html#configure-autoscaling-for-your-table
		const ChatMessageHistoryTable = new dynamodb.Table(
			this,
			"ChatHistoryTable",
			{
				// consider activating the encryption by uncommenting the code below.
				// encryption: dynamodb.TableEncryption.AWS_MANAGED,
				partitionKey: {
					name: "SessionId",
					type: dynamodb.AttributeType.STRING,
				},
				billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
				// Considerations when choosing a table class
				// https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithTables.tableclasses.html
				tableClass: dynamodb.TableClass.STANDARD,
				// When moving to production, use cdk.RemovalPolicy.RETAIN instead
				// which will keep the database table when destroying the stack.
				// this avoids accidental deletion of user data.
				removalPolicy: cdk.RemovalPolicy.DESTROY,
				encryption: dynamodb.TableEncryption.AWS_MANAGED,
			}
		);

		// -----------------------------------------------------------------------
		var currentNetworkMode = NetworkMode.DEFAULT;
		// if you run the cdk stack in SageMaker editor, you need to pass --network sagemaker
		// for docker build to work. The following achieve that.
		// if (process.env.SAGEMAKER_APP_TYPE) {
		// 	currentNetworkMode = NetworkMode.custom("sagemaker");
		// }

		// Add AWS Lambda container and function to serve as the agent executor.
		// const agent_executor_lambda = new lambda.DockerImageFunction(
		// 	this,
		// 	"LambdaAgentContainer",
		// 	{
		// 		code: lambda.DockerImageCode.fromImageAsset(
		// 			path.join(
		// 				__dirname,
		// 				"lambda-functions/agent-executor-lambda-container"
		// 			),
		// 			{
		// 				networkMode: currentNetworkMode,
		// 				buildArgs: { "--platform": "linux/amd64" },
		// 			}
		// 		),
		// 		description: "Lambda function with bedrock access created via CDK",
		// 		timeout: cdk.Duration.minutes(3),
		// 		memorySize: 2048,
		// 		// vpc: vpc.vpc,
		// 		environment: {
		// 			BEDROCK_REGION_PARAMETER: ssm_bedrock_region_parameter.parameterName,
		// 			LLM_MODEL_ID_PARAMETER: ssm_llm_model_id_parameter.parameterName,
		// 			CHAT_MESSAGE_HISTORY_TABLE: ChatMessageHistoryTable.tableName,
		// 			AGENT_DB_SECRET_ID: AgentDB.secret?.secretArn as string,
		// 		},
		// 	}
		// );
		const pythonLayer = lambda.LayerVersion.fromLayerVersionArn(
			this,
			"MyPythonLayer",
			"arn:aws:lambda:us-east-1:381491977872:layer:agent-layer:1"
		);
		const agent_executor_lambda = new lambda.Function(
			this,
			"LambdaAgentHandler",
			{
				runtime: lambda.Runtime.PYTHON_3_12, // Replace with the runtime for your code
				code: lambda.Code.fromAsset(
					path.join(__dirname, "lambda-functions", "agent-executor-single")
				), // Replace with the path to your new function code
				layers: [pythonLayer],
				handler: "handler.lambda_handler", // The entry point of your function
				description: "Lambda function with Bedrock access created via CDK",
				timeout: cdk.Duration.minutes(2),
				memorySize: 1024,
				environment: {
					BEDROCK_REGION_PARAMETER: ssm_bedrock_region_parameter.parameterName,
					LLM_MODEL_ID_PARAMETER: ssm_llm_model_id_parameter.parameterName,
					CHAT_MESSAGE_HISTORY_TABLE: ChatMessageHistoryTable.tableName,
					AGENT_DB_SECRET_ID: AgentDB.secret?.secretArn as string,
				},
			}
		);
		const agent_api_lambda = new lambda.Function(this, "LambdaAgentAPI", {
			runtime: lambda.Runtime.PYTHON_3_12, // Replace with the runtime for your code
			code: lambda.Code.fromAsset(
				path.join(__dirname, "lambda-functions", "agent-executor-api")
			), // Replace with the path to your new function code
			layers: [pythonLayer],
			handler: "handler.lambda_handler", // The entry point of your function
			description: "Lambda function for update data",
			timeout: cdk.Duration.minutes(2),
			memorySize: 512,
			environment: {
				BEDROCK_REGION_PARAMETER: ssm_bedrock_region_parameter.parameterName,
				LLM_MODEL_ID_PARAMETER: ssm_llm_model_id_parameter.parameterName,
				CHAT_MESSAGE_HISTORY_TABLE: ChatMessageHistoryTable.tableName,
				AGENT_DB_SECRET_ID: AgentDB.secret?.secretArn as string,
			},
		});
		const agent_executor_get = new lambda.Function(this, "LambdaAgentGetAPI", {
			runtime: lambda.Runtime.PYTHON_3_12, // Replace with the runtime for your code
			code: lambda.Code.fromAsset(
				path.join(__dirname, "lambda-functions", "agent-executor-get")
			), // Replace with the path to your new function code
			layers: [pythonLayer],
			handler: "handler.lambda_handler", // The entry point of your function
			description: "Lambda function for get data from database API",
			timeout: cdk.Duration.minutes(2),
			memorySize: 512,
			environment: {
				BEDROCK_REGION_PARAMETER: ssm_bedrock_region_parameter.parameterName,
				LLM_MODEL_ID_PARAMETER: ssm_llm_model_id_parameter.parameterName,
				CHAT_MESSAGE_HISTORY_TABLE: ChatMessageHistoryTable.tableName,
				AGENT_DB_SECRET_ID: AgentDB.secret?.secretArn as string,
			},
		});
		// Placeholder Step 2.4 - grant Lambda permission to access db credentials
		// Allow Lambda to read the secret for Aurora DB connection.
		AgentDB.secret?.grantRead(agent_executor_lambda);
		AgentDB.secret?.grantRead(agent_api_lambda);
		AgentDB.secret?.grantRead(agent_executor_get);

		// Allow network access to/from Lambda
		// AgentDB.connections.allowDefaultPortFrom(agent_executor_lambda);
		// This only use in Testing/ Dev
		AgentDB.connections.allowFromAnyIpv4(
			ec2.Port.tcp(AgentDB.instanceEndpoint.port)
		);
		// ----
		// Allow Lambda to read SSM parameters.
		ssm_bedrock_region_parameter.grantRead(agent_executor_lambda);
		ssm_llm_model_id_parameter.grantRead(agent_executor_lambda);
		ssm_bedrock_region_parameter.grantRead(agent_api_lambda);
		ssm_llm_model_id_parameter.grantRead(agent_api_lambda);
		ssm_bedrock_region_parameter.grantRead(agent_executor_get);
		ssm_llm_model_id_parameter.grantRead(agent_executor_get);
		// -----------------------------------------------------------------------
		// Save the secret ARN for the database in an SSM parameter to simplify
		const ssm_database_secret = new ssm.StringParameter(
			this,
			"ssmBedrockDatabaseSecret",
			{
				parameterName: "/AgenticLLMAssistantWorkshop/DBSecretARN",
				// This is the default region.
				// The user can update it in parameter store.
				stringValue: AgentDB.secret?.secretArn as string,
			}
		);
		ssm_database_secret.grantRead(agent_executor_lambda);
		ssm_database_secret.grantRead(agent_api_lambda);
		ssm_database_secret.grantRead(agent_executor_get);
		// Allow Lambda read/write access to the chat history DynamoDB table
		// to be able to read and update it as conversations progress.
		ChatMessageHistoryTable.grantReadWriteData(agent_executor_lambda);
		ChatMessageHistoryTable.grantReadWriteData(agent_api_lambda);
		ChatMessageHistoryTable.grantReadWriteData(agent_executor_get);

		// Allow the Lambda function to use Bedrock
		agent_executor_lambda.role?.addManagedPolicy(
			iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonBedrockFullAccess")
		);
		agent_api_lambda.role?.addManagedPolicy(
			iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonBedrockFullAccess")
		);
		agent_executor_get.role?.addManagedPolicy(
			iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonBedrockFullAccess")
		);

		// Save the Lambda ARN in an SSM parameter to simplify invoking the lambda
		// from a SageMaker notebook, without having to copy it manually.
		const agentLambdaNameParameter = new ssm.StringParameter(
			this,
			"AgentLambdaNameParameter",
			{
				parameterName:
					"/AgenticLLMAssistantWorkshop/AgentExecutorLambdaNameParameter",
				stringValue: agent_executor_lambda.functionName,
			}
		);

		//------------------------------------------------------------------------
		// Create an S3 bucket for intermediate data staging
		// and allow SageMaker to read and write to it.
		const agent_data_bucket = new s3.Bucket(this, "AgentDataBucket", {
			// Warning, swith DESTROY to RETAIN to avoid accidental deletion
			// of important data.
			removalPolicy: cdk.RemovalPolicy.DESTROY,
			autoDeleteObjects: true,
		});

		// Save the bucket name as an SSM parameter to simplify using it in
		// SageMaker processing jobs without having to copy the name manually.
		const agentDataBucketParameter = new ssm.StringParameter(
			this,
			"AgentDataBucketParameter",
			{
				parameterName: "/AgenticLLMAssistantWorkshop/AgentDataBucketParameter",
				stringValue: agent_data_bucket.bucketName,
			}
		);

		// 	{
		// 		"Sid": "PublicReadGetObject",
		// 		"Effect": "Allow",
		// 		"Principal": "*",
		// 		"Action": "s3:GetObject",
		// 		"Resource": "arn:aws:s3:::your-bucket-name/*"
		// }
		agentDataBucketParameter.grantRead(agent_executor_lambda);
		agentDataBucketParameter.grantWrite(agent_executor_lambda);
		agentDataBucketParameter.grantRead(agent_api_lambda);
		agent_data_bucket.grantReadWrite(agent_api_lambda);
		agentDataBucketParameter.grantRead(agent_executor_get);

		// -----------------------------------------------------------------------
		// Create a managed IAM policy to be attached to a SageMaker execution role
		// to allow the required permissions to retrieve the information to access the database.
		// new SageMakerIAMPolicyConstruct(this, "SageMakerIAMPolicy", {
		// 	bedrockRegionParameter: ssm_bedrock_region_parameter,
		// 	llmModelIdParameter: ssm_llm_model_id_parameter,
		// 	agentDataBucketParameter: agentDataBucketParameter,
		// 	agentLambdaNameParameter: agentLambdaNameParameter,
		// 	agentDataBucket: agent_data_bucket,
		// 	agentExecutorLambda: agent_executor_lambda,
		// 	rdsCluster: AgentDB,
		// 	sagemaker_rds_access: sagemaker_rds_access,
		// });

		// -----------------------------------------------------------------------
		// Create a new Cognito user pool and add an app client to the user pool

		const cognito_authorizer = new CognitoConstruct(this, "Cognito");
		// -------------------------------------------------------------------------
		// Add an Amazon API Gateway with AWS cognito auth and an AWS lambda as a backend
		new AssistantApiConstruct(this, "AgentApi", {
			cognitoUserPool: cognito_authorizer.userPool,
			lambdaFunction: agent_executor_lambda,
			apiFunction: agent_api_lambda,
			getFunction: agent_executor_get,
		});

		// new SageMakerProcessor(this, "SagemakerProcessor");
	}
}
