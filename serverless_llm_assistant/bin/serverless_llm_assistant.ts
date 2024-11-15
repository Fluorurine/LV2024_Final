#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { ServerlessLlmAssistantStack } from "../lib/serverless_llm_assistant-stack";

const app = new cdk.App();
new ServerlessLlmAssistantStack(app, "ServerlessLlmAssistantStack", {
	/* If you don't specify 'env', this stack will be environment-agnostic.
	 * Account/Region-dependent features and context lookups will not work,
	 * but a single synthesized template can be deployed anywhere. */
	/* Uncomment the next line if you know exactly what Account and Region you
	 * want to deploy the stack to. */
	// env: {
	// 	account: process.env.CDK_DEFAULT_ACCOUNT,
	// 	region: process.env.CDK_DEFAULT_REGION,
	// },

	env: { account: "381491977872", region: "us-east-1" },
	description: "AWS Agentic documents assistant by Truong",
	/* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});
