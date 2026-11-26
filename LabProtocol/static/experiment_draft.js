(function () {
    const body = document.body;
    const stage = body.dataset.stage;
    const key = "labprotocol-draft-" + body.dataset.methodId;
    const setupKey = key + "-setup";
    const navigation = performance.getEntriesByType("navigation")[0];
    const historyDraft = history.state && history.state.labProtocolDraft;
    const notice = document.getElementById("draft-notice");

    function showNotice(message) {
        let target = notice;
        if (!target) {
            target = document.createElement("div");
            target.className = "warning";
            target.setAttribute("role", "status");
            document.querySelector("h1").after(target);
        }
        target.hidden = false;
        target.textContent = message;
    }

    function readDraft(storageKey = key) {
        try {
            const value = sessionStorage.getItem(storageKey);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            showNotice("This browser could not restore the setup draft. Check your entries before continuing.");
            return null;
        }
    }

    function writeDraft(draft, storageKey = key) {
        try {
            sessionStorage.setItem(storageKey, JSON.stringify(draft));
        } catch (error) {
            showNotice("This browser could not save the setup draft. Going back may lose your entries.");
        }
    }

    function saveHistory(draft) {
        try {
            history.replaceState(
                { ...history.state, labProtocolDraft: draft }, ""
            );
        } catch (error) {
            showNotice("This browser could not save this page's entries. Going back may lose them.");
        }
    }

    function values(selector) {
        return Array.from(document.querySelectorAll(selector), input => input.value);
    }

    function setValues(selector, data) {
        document.querySelectorAll(selector).forEach((input, index) => {
            if (index < data.length) input.value = data[index];
        });
    }

    function matchingIndex(items, index, previousItems) {
        const key = JSON.stringify(items[index]);
        const occurrence = items.slice(0, index).filter(
            item => JSON.stringify(item) === key
        ).length;
        const matches = previousItems.reduce((indices, item, oldIndex) => {
            if (JSON.stringify(item) === key) indices.push(oldIndex);
            return indices;
        }, []);
        return matches[occurrence] === undefined ? -1 : matches[occurrence];
    }

    function setupSnapshot() {
        return {
            stage: "setup",
            strains: values("#strain-list input"),
            treatments: values("#treatment-list input"),
            strainOrigins: Array.from(document.querySelectorAll("#strain-list .strain-row"),
                row => row.dataset.originalName || ""),
            treatmentOrigins: Array.from(document.querySelectorAll("#treatment-list .strain-row"),
                row => row.dataset.originalName || ""),
            replicates: document.getElementById("default-group-replicates").value,
            cultureFormat: document.getElementById("culture-format").value
        };
    }

    function restoreSetup(draft) {
        for (const [listId, entries, origins, add] of [
            ["strain-list", draft.strains, draft.strainOrigins || [], addStrain],
            ["treatment-list", draft.treatments, draft.treatmentOrigins || [], addTreatment]
        ]) {
            const list = document.getElementById(listId);
            list.replaceChildren();
            entries.forEach(() => add());
            setValues("#" + listId + " input", entries);
            list.querySelectorAll(".strain-row").forEach((row, index) => {
                row.dataset.originalName = origins[index] || "";
            });
        }
        document.getElementById("default-group-replicates").value = draft.replicates;
        document.getElementById("culture-format").value = draft.cultureFormat;
    }

    function detailsSnapshot() {
        const form = document.getElementById("nucleic-acid-form");
        const strains = values('#nucleic-acid-form input[name="strains"]');
        const treatments = values('#nucleic-acid-form input[name="treatments"]');
        const groups = strains.flatMap(strain =>
            treatments.map(treatment => [strain, treatment])
        );
        const fields = {};
        form.querySelectorAll('input:not([type="hidden"])').forEach(input => {
            if (!input.name.startsWith("acid_")) fields[input.name] = input.value;
        });
        return {
            stage: "details",
            treatments,
            groups,
            groupValues: groups.map((group, index) =>
                document.querySelector(`[name="group_replicates_${index}"]`).value
            ),
            fields,
            acids: treatments.map((treatment, index) =>
                Array.from(document.querySelectorAll(`#acid-list-${index} .acid-row`), row =>
                    Array.from(row.querySelectorAll("input"), input => input.value)
                )
            )
        };
    }

    function restoreDetails(draft, setup) {
        const form = document.getElementById("nucleic-acid-form");
        const current = detailsSnapshot();
        const strains = values('#nucleic-acid-form input[name="strains"]');
        const oldStrains = strains.map((name, index) =>
            setup && setup.strains[index] === name ? setup.strainOrigins[index] || name : name
        );
        const oldTreatments = current.treatments.map((name, index) =>
            setup && setup.treatments[index] === name ? setup.treatmentOrigins[index] || name : name
        );
        const oldGroups = oldStrains.flatMap(strain =>
            oldTreatments.map(treatment => [strain, treatment])
        );
        Object.entries(draft.fields).forEach(([name, value]) => {
            const input = form.elements.namedItem(name);
            if (input) input.value = value;
        });
        current.groups.forEach((group, index) => {
            const oldIndex = matchingIndex(oldGroups, index, draft.groups);
            if (oldIndex >= 0) {
                document.querySelector(`[name="group_replicates_${index}"]`).value =
                    draft.groupValues[oldIndex];
            }
        });
        let unmatched = false;
        let renamed = false;
        current.treatments.forEach((treatment, index) => {
            const oldIndex = matchingIndex(oldTreatments, index, draft.treatments);
            if (oldIndex < 0) {
                unmatched = true;
                return;
            }
            if (treatment !== oldTreatments[index]) renamed = true;
            const list = document.getElementById("acid-list-" + index);
            list.replaceChildren();
            draft.acids[oldIndex].forEach(rowValues => {
                addNucleicAcid(index);
                const row = list.lastElementChild;
                row.querySelectorAll("input").forEach((input, position) => {
                    input.value = rowValues[position];
                });
            });
        });
        if (unmatched) {
            showNotice("New or renamed treatments use default plasmid rows. Check their contents before continuing.");
        } else if (renamed) {
            showNotice("A treatment was renamed. Review its restored plasmid names and contents before continuing.");
        }
    }

    function updateTreatmentWellCounts() {
        const strains = values('#nucleic-acid-form input[name="strains"]');
        const treatments = values('#nucleic-acid-form input[name="treatments"]');
        treatments.forEach((treatment, treatmentIndex) => {
            let total = 0;
            let valid = true;
            strains.forEach((strain, strainIndex) => {
                treatments.forEach((groupTreatment, groupIndex) => {
                    if (groupTreatment !== treatment) return;
                    const input = document.querySelector(
                        `[name="group_replicates_${strainIndex * treatments.length + groupIndex}"]`
                    );
                    const count = Number(input.value);
                    if (!Number.isInteger(count) || count < 1) valid = false;
                    else total += count;
                });
            });
            document.querySelector(`[data-treatment-wells="${treatmentIndex}"]`).textContent =
                valid ? String(total) : "Check group counts";
        });
    }

    if (stage === "setup") {
        if (body.dataset.requestMethod === "GET" && !historyDraft &&
                (!navigation || navigation.type !== "back_forward")) {
            try {
                sessionStorage.removeItem(key);
                sessionStorage.removeItem(setupKey);
            } catch (error) {
                showNotice("This browser could not clear the previous draft. Check your entries before continuing.");
            }
        }
        const restore = () => {
            const draft = history.state && history.state.labProtocolDraft;
            if (draft && draft.stage === "setup") restoreSetup(draft);
        };
        restore();
        window.addEventListener("pageshow", restore);
        document.querySelectorAll("#strain-list .strain-row, #treatment-list .strain-row").forEach(row => {
            if (!row.dataset.originalName) row.dataset.originalName = row.querySelector("input").value;
        });
        const save = () => saveHistory(setupSnapshot());
        document.getElementById("experiment-form").addEventListener("submit", () => {
            document.querySelectorAll("#strain-list .strain-row, #treatment-list .strain-row").forEach(row => {
                if (!row.dataset.originalName) row.dataset.originalName = row.querySelector("input").value;
            });
            const draft = setupSnapshot();
            saveHistory(draft);
            writeDraft(draft, setupKey);
        });
        document.addEventListener("input", save);
        document.addEventListener("change", save);
        document.addEventListener("click", event => {
            if (event.target.closest("button[type=button]")) save();
        });
    } else if (stage === "details") {
        const draft = historyDraft && historyDraft.stage === "details"
            ? historyDraft
            : body.dataset.requestStage === "setup" || body.dataset.hasError === "true"
                ? readDraft() : null;
        if (draft && draft.stage === "details") {
            const setup = body.dataset.requestStage === "setup" ? readDraft(setupKey) : null;
            restoreDetails(draft, setup);
        }
        updateTreatmentWellCounts();
        window.addEventListener("pageshow", event => {
            const saved = history.state && history.state.labProtocolDraft;
            if (event.persisted && saved && saved.stage === "details") {
                restoreDetails(saved);
                updateTreatmentWellCounts();
            }
        });
        const save = () => {
            updateTreatmentWellCounts();
            const current = detailsSnapshot();
            saveHistory(current);
            writeDraft(current);
        };
        document.getElementById("nucleic-acid-form").addEventListener("submit", save);
        document.addEventListener("input", save);
        document.addEventListener("change", save);
        document.addEventListener("click", event => {
            if (event.target.closest("button[type=button]")) save();
        });
    }
})();
