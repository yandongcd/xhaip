(function () {
  'use strict';

  var debounce = function (fn, ms) {
    var t;
    return function () {
      var args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(null, args); }, ms);
    };
  };

  var store = {
    get: function (k) {
      try { return localStorage.getItem(k); } catch (_) { return null; }
    },
    set: function (k, v) {
      try { localStorage.setItem(k, v); } catch (_) {}
    },
  };

  function tierClass(score) {
    if (score >= 80) return 'l3';
    if (score >= 50) return 'l2';
    if (score >= 20) return 'l1';
    return 'l0';
  }

  function tierLabel(score) {
    if (score >= 80) return 'L3 成熟';
    if (score >= 50) return 'L2 发展中';
    if (score >= 20) return 'L1 起步';
    return 'L0 未覆盖';
  }

  function sortDepts(depts, key, dir) {
    var copy = depts.slice();
    copy.sort(function (a, b) {
      var va = key === 'name' ? a[key] : (a[key] || 0);
      var vb = key === 'name' ? b[key] : (b[key] || 0);
      if (key === 'name') {
        return dir === 'asc' ? va.localeCompare(vb, 'zh') : vb.localeCompare(va, 'zh');
      }
      return dir === 'asc' ? va - vb : vb - va;
    });
    return copy;
  }

  function groupByType(depts) {
    var map = {};
    for (var i = 0; i < depts.length; i++) {
      var d = depts[i];
      if (!map[d.type]) map[d.type] = [];
      map[d.type].push(d);
    }
    var types = Object.keys(map).sort();
    var result = [];
    for (var j = 0; j < types.length; j++) {
      var t = types[j];
      map[t].sort(function (a, b) { return b.score - a.score; });
      result.push({ type: t, depts: map[t], count: map[t].length });
    }
    return result;
  }

  function exportCSV(depts) {
    var header = '\uFEFF\u79D1\u5BA4,\u7C7B\u578B,\u8BC4\u5206,\u7B49\u7EA7,\u9636\u6BB5,\u89D2\u8272,Agent,\u6821\u9A8C,Gap';
    var rows = [];
    for (var i = 0; i < depts.length; i++) {
      var d = depts[i];
      rows.push(
        '"' + d.name + '","' + d.type + '",' + d.score + ',"' + d.tier + '",' +
        d.stages + ',' + d.roles + ',"' + (d.agent || '\u2014') + '","' +
        (d.validation_passed ? '\u901A\u8FC7' : '\u2014') + '","' +
        (d.gaps || []).join('; ') + '"'
      );
    }
    var csv = [header].concat(rows).join('\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'xhaip-dashboard-' + new Date().toISOString().slice(0, 10) + '.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('dashboard', function () {
      return {
        depts: DASHBOARD_DATA.depts || [],
        deptAgentsMap: DASHBOARD_DATA.dept_agents || {},
        tiers: DASHBOARD_DATA.tiers || {},
        avg_score: DASHBOARD_DATA.avg_score || 0,
        total: DASHBOARD_DATA.total || 0,
        error: DASHBOARD_DATA.error || null,
        theme: store.get('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
        searchQuery: '',
        typeFilters: [],
        tierFilters: [],
        typeDropdownOpen: false,
        tierDropdownOpen: false,
        sortKey: 'score',
        sortDir: 'desc',
        selectedDept: null,
        showDimensions: false,
        exportOpen: false,

        get allTypes() {
          var set = {};
          for (var i = 0; i < this.depts.length; i++) {
            set[this.depts[i].type] = true;
          }
          return Object.keys(set).sort();
        },

        get filteredDepts() {
          var result = this.depts;
          if (this.searchQuery) {
            var q = this.searchQuery.toLowerCase();
            result = result.filter(function (d) {
              return d.name.toLowerCase().indexOf(q) !== -1;
            });
          }
          if (this.typeFilters.length) {
            var tf = this.typeFilters;
            result = result.filter(function (d) {
              return tf.indexOf(d.type) !== -1;
            });
          }
          if (this.tierFilters.length) {
            var rf = this.tierFilters;
            result = result.filter(function (d) {
              return rf.indexOf(d.tier) !== -1;
            });
          }
          return sortDepts(result, this.sortKey, this.sortDir);
        },

        get groups() {
          return groupByType(this.filteredDepts);
        },

        get noResults() {
          return !this.error && this.filteredDepts.length === 0;
        },

        get deptAgents() {
          if (!this.selectedDept) return [];
          return this.deptAgentsMap[this.selectedDept.name] || [];
        },

        get agentTypeLabel() {
          var labels = {
            business: '业务',
            specialist: '专科',
            master_data: '主数据',
            architecture: '架构',
          };
          return function (t) { return labels[t] || t; };
        },

        goToAgent: function (agent) {
          window.location.href = '/agent/' + agent.name;
        },

        init: function () {
          this.applyTheme();
          var self = this;
          window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
            if (!store.get('theme')) {
              self.theme = e.matches ? 'dark' : 'light';
              self.applyTheme();
            }
          });
        },

        toggleTheme: function () {
          this.theme = this.theme === 'dark' ? 'light' : 'dark';
          store.set('theme', this.theme);
          this.applyTheme();
        },

        applyTheme: function () {
          document.documentElement.setAttribute('data-theme', this.theme);
        },

        clearSearch: function () {
          this.searchQuery = '';
        },

        toggleTypeFilter: function () {
          this.typeDropdownOpen = !this.typeDropdownOpen;
          this.tierDropdownOpen = false;
          this.exportOpen = false;
        },

        toggleTierFilter: function () {
          this.tierDropdownOpen = !this.tierDropdownOpen;
          this.typeDropdownOpen = false;
          this.exportOpen = false;
        },

        isTypeChecked: function (type) {
          return this.typeFilters.indexOf(type) >= 0;
        },

        toggleType: function (type) {
          var idx = this.typeFilters.indexOf(type);
          if (idx >= 0) this.typeFilters.splice(idx, 1);
          else this.typeFilters.push(type);
        },

        isTierChecked: function (tier) {
          return this.tierFilters.indexOf(tier) >= 0;
        },

        toggleTier: function (tier) {
          var idx = this.tierFilters.indexOf(tier);
          if (idx >= 0) this.tierFilters.splice(idx, 1);
          else this.tierFilters.push(tier);
        },

        setSort: function (key) {
          if (this.sortKey === key) {
            this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
          } else {
            this.sortKey = key;
            this.sortDir = 'desc';
          }
        },

        sortIndicator: function (key) {
          if (this.sortKey !== key) return '';
          return this.sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
        },

        selectDept: function (dept) {
          this.selectedDept = this.selectedDept === dept ? null : dept;
        },

        closeDrilldown: function () {
          this.selectedDept = null;
          this.showDimensions = false;
        },

        toggleDimensionsTab: function () {
          this.showDimensions = !this.showDimensions;
        },

        toggleExport: function () {
          this.exportOpen = !this.exportOpen;
          this.typeDropdownOpen = false;
          this.tierDropdownOpen = false;
        },

        doExportCSV: function () {
          exportCSV(this.filteredDepts);
          this.exportOpen = false;
        },

        doExportPDF: function () {
          this.exportOpen = false;
          window.print();
        },

        tierClass: tierClass,
        tierLabel: tierLabel,

        tierPct: function (tier) {
          if (!this.total) return 0;
          return ((this.tiers[tier] || 0) / this.total * 100).toFixed(0);
        },

        retry: function () {
          window.location.reload();
        },
      };
    });
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.dropdown') && !e.target.closest('.export-dropdown')) {
      var panels = document.querySelectorAll('.dropdown-panel.open, .export-panel.open');
      for (var i = 0; i < panels.length; i++) {
        panels[i].classList.remove('open');
      }
    }
  });
})();
