NAMESPACE=kfops
.PHONY: develop run_workflow clean_workflows

develop:
	@skaffold dev --filename development/skaffold.yaml
# --trigger polling

run_workflow:
	argo submit development/manual-workflow-submit.yaml \
		-p "pr-comment=$(command)" \
		-p "pr-number=dummy" \
		-p "repo-owner=dummy" \
		-p "repo-name=dummy" \
		--watch -n $(NAMESPACE)

clean_workflows:
	@argo delete --all -n $(NAMESPACE)
	@kubectl delete po -l name=cluster-image-builder -n $(NAMESPACE)