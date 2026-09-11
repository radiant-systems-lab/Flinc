// Called from the existing commands-toolkit plugin's activate(app).
function registerFlincNotebookCommands(app) {
  async function openNotebook(path, kernelName) {
    if (typeof path !== 'string' || !path.endsWith('.ipynb')) throw new Error('A notebook path is required');
    const panel = await app.commands.execute('docmanager:open', {
      // Open without auto-starting the kernel recorded in notebook metadata.
      path, ...(kernelName ? {kernelPreference: {shouldStart: false, shouldReuse: false}} : {})
    });
    if (!panel?.sessionContext) throw new Error('The requested document is not a notebook');
    await panel.context.ready;
    // A deliberately kernel-less document is not session-ready until selection.
    if (!kernelName) await panel.sessionContext.ready;
    const kernel = panel.sessionContext.session?.kernel;
    if (kernel) await kernel.info;
    return panel;
  }
  app.commands.addCommand('jupyterlab-commands-toolkit:select-notebook-kernel', {
    label: 'Select Notebook Kernel',
    describedBy: {args: {type: 'object', properties: {path: {type: 'string'}, kernelName: {type: 'string'}}, required: ['path', 'kernelName']}},
    execute: async ({path, kernelName}) => {
      await app.serviceManager.kernelspecs.ready;
      if (!app.serviceManager.kernelspecs.specs?.kernelspecs[kernelName]) throw new Error(`Unknown kernel: ${kernelName}`);
      const panel = await openNotebook(path, kernelName);
      const current = panel.sessionContext.session?.kernel;
      if (current?.name === kernelName) return {success: true, kernel_name: kernelName, changed: false};
      if (current && ['busy', 'starting', 'restarting'].includes(current.status)) throw new Error('The current kernel is busy; wait or explicitly interrupt it first');
      // Sciunit must commit Audit before Repeat can acquire the project lock.
      if (current) await panel.sessionContext.shutdown();
      await panel.sessionContext.changeKernel({name: kernelName});
      const selected = panel.sessionContext.session?.kernel;
      if (!selected) throw new Error('Kernel selection did not start a kernel');
      await selected.info;
      const deadline = Date.now() + 120000;
      while (selected.status !== 'idle') {
        if (Date.now() > deadline || ['dead', 'terminating'].includes(selected.status)) throw new Error('Selected kernel did not become ready');
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      await panel.context.save();
      return {success: true, kernel_name: panel.sessionContext.session?.kernel?.name, changed: true};
    }
  });
  const running = new Set();
  app.commands.addCommand('jupyterlab-commands-toolkit:shutdown-notebook', {
    label: 'Finalize Notebook Kernel',
    describedBy: {args: {type: 'object', properties: {path: {type: 'string'}}, required: ['path']}},
    execute: async ({path}) => {
      if (running.has(path)) throw new Error('Wait for the notebook run to finish');
      const panel = await openNotebook(path);
      const kernel = panel.sessionContext.session?.kernel;
      if (kernel && ['busy', 'starting', 'restarting'].includes(kernel.status)) throw new Error('The kernel is busy');
      await panel.context.save();
      await panel.sessionContext.shutdown();
      // Remove the tab from workspace restoration so Audit is not restarted.
      panel.dispose();
      return {success: true, notebook_path: path, kernel_shutdown: true};
    }
  });
  app.commands.addCommand('jupyterlab-commands-toolkit:run-notebook', {
    label: 'Run Notebook by Path',
    describedBy: {args: {type: 'object', properties: {path: {type: 'string'}}, required: ['path']}},
    execute: async ({path}) => {
      if (running.has(path)) throw new Error('This notebook already has a run in progress');
      running.add(path);
      let panel;
      try {
        panel = await openNotebook(path);
        if (panel.sessionContext.session?.kernel?.status !== 'idle') throw new Error('The notebook kernel is not idle: ' + panel.sessionContext.session?.kernel?.status);
        await panel.context.save();
        // The built-in command captures the active panel before its first await.
        app.shell.activateById(panel.id);
        return await app.commands.execute('notebook:run-all-cells');
      } finally {
        try {
          if (panel && !panel.isDisposed) await panel.context.save();
        } finally {
          running.delete(path);
        }
      }
    }
  });
}
