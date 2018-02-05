NAME = tuned
# set to devel for nightly GIT snapshot
BUILD = release
# which config to use in mock-build target
MOCK_CONFIG = rhel-7-x86_64
# scratch-build for triggering Jenkins
SCRATCH_BUILD_TARGET = rhel-7.5-candidate
KVM_UNIT_TESTS_SNAP = 20171020
KVM_UNIT_TESTS = kvm-unit-tests-$(KVM_UNIT_TESTS_SNAP).tar.gz
KVM_UNIT_TESTS_URL = https://git.kernel.org/pub/scm/virt/kvm/kvm-unit-tests.git/snapshot/$(KVM_UNIT_TESTS)
VERSION = $(shell awk '/^Version:/ {print $$2}' tuned.spec)
GIT_DATE = $(shell date +'%Y%m%d')
ifeq ($(BUILD), release)
	RPM_ARGS += --without snapshot
	MOCK_ARGS += --without=snapshot
	RPM_VERSION = $(NAME)-$(VERSION)-1
else
	RPM_ARGS += --with snapshot
	MOCK_ARGS += --with=snapshot
	GIT_SHORT_COMMIT = $(shell git rev-parse --short=8 --verify HEAD)
	GIT_SUFFIX = $(GIT_DATE)git$(GIT_SHORT_COMMIT)
	GIT_PSUFFIX = .$(GIT_SUFFIX)
	RPM_VERSION = $(NAME)-$(VERSION)-1$(GIT_PSUFFIX)
endif
UNITDIR_FALLBACK = /usr/lib/systemd/system
UNITDIR_DETECT = $(shell pkg-config systemd --variable systemdsystemunitdir || rpm --eval '%{_unitdir}' 2>/dev/null || echo $(UNITDIR_FALLBACK))
UNITDIR = $(UNITDIR_DETECT:%{_unitdir}=$(UNITDIR_FALLBACK))
TMPFILESDIR_FALLBACK = /usr/lib/tmpfiles.d
TMPFILESDIR_DETECT = $(shell pkg-config systemd --variable tmpfilesdir || rpm --eval '%{_tmpfilesdir}' 2>/dev/null || echo $(TMPFILESDIR_FALLBACK))
TMPFILESDIR = $(TMPFILESDIR_DETECT:%{_tmpfilesdir}=$(TMPFILESDIR_FALLBACK))
VERSIONED_NAME = $(NAME)-$(VERSION)$(GIT_PSUFFIX)

SYSCONFDIR = /etc
DATADIR = /usr/share
DOCDIR = $(DATADIR)/doc/$(NAME)
PYTHON = python3
PYLINT = pylint-3
ifeq ($(PYTHON),python2)
PYLINT = pylint-2
endif
SHEBANG_REWRITE_REGEX= '1s/^(\#!\/usr\/bin\/)\<python\>/\1$(PYTHON)/'
PYTHON_SITELIB = $(shell $(PYTHON) -c 'from distutils.sysconfig import get_python_lib; print(get_python_lib());')
ifeq ($(PYTHON_SITELIB),)
$(error Failed to determine python library directory)
endif
TUNED_PROFILESDIR = /usr/lib/tuned
TUNED_RECOMMEND_DIR = $(TUNED_PROFILESDIR)/recommend.d
TUNED_USER_RECOMMEND_DIR = $(SYSCONFDIR)/tuned/recommend.d
BASH_COMPLETIONS = $(DATADIR)/bash-completion/completions

release-dir:
	mkdir -p $(VERSIONED_NAME)

release-cp: release-dir
	cp -a AUTHORS COPYING INSTALL README $(VERSIONED_NAME)

	cp -a tuned.py tuned.spec tuned.service tuned.tmpfiles Makefile tuned-adm.py \
		tuned-adm.bash dbus.conf recommend.conf tuned-main.conf 00_tuned \
		bootcmdline modules.conf com.redhat.tuned.policy \
		com.redhat.tuned.gui.policy tuned-gui.py tuned-gui.glade \
		tuned-gui.desktop setup.py $(VERSIONED_NAME)
	cp -a doc experiments libexec man profiles systemtap tuned contrib icons \
		$(VERSIONED_NAME)

archive: clean release-cp
	tar czf $(VERSIONED_NAME).tar.gz $(VERSIONED_NAME)

rpm-build-dir:
	mkdir rpm-build-dir

$(KVM_UNIT_TESTS):
	wget '$(KVM_UNIT_TESTS_URL)'

srpm: $(KVM_UNIT_TESTS) archive rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps $(RPM_ARGS) -ts $(VERSIONED_NAME).tar.gz

rpm: archive rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps $(RPM_ARGS) -tb $(VERSIONED_NAME).tar.gz

clean-mock-result-dir:
	rm -f mock-result-dir/*

mock-result-dir:
	mkdir mock-result-dir

# delete RPM files older than cca. one week if total space occupied is more than 5 MB
tidy-mock-result-dir: mock-result-dir
	if [ `du -bs mock-result-dir | tail -n 1 | cut -f1` -gt 5000000 ]; then \
		rm -f `find mock-result-dir -name '*.rpm' -mtime +7`; \
	fi

mock-build: srpm
	mock -r $(MOCK_CONFIG) $(MOCK_ARGS) --resultdir=`pwd`/mock-result-dir `ls rpm-build-dir/*$(RPM_VERSION).*.src.rpm | head -n 1`&& \
	rm -f mock-result-dir/*.log

mock-devel-build: srpm
	mock -r $(MOCK_CONFIG) --with=snapshot \
		--define "git_short_commit `if [ -n \"$(GIT_SHORT_COMMIT)\" ]; then echo $(GIT_SHORT_COMMIT); else git rev-parse --short=8 --verify HEAD; fi`" \
		--resultdir=`pwd`/mock-result-dir `ls rpm-build-dir/*$(RPM_VERSION).*.src.rpm | head -n 1` && \
	rm -f mock-result-dir/*.log

createrepo: mock-devel-build
	createrepo mock-result-dir

# scratch build to triggering Jenkins
scratch-build: mock-devel-build
	brew build --scratch --nowait $(SCRATCH_BUILD_TARGET) `ls mock-result-dir/*$(GIT_DATE)git*.*.src.rpm | head -n 1`

nightly: tidy-mock-result-dir createrepo scratch-build
	rsync -ave ssh --delete --progress mock-result-dir/ jskarvad@fedorapeople.org:/home/fedora/jskarvad/public_html/tuned/devel/repo/

install-dirs:
	mkdir -p $(DESTDIR)$(PYTHON_SITELIB)
	mkdir -p $(DESTDIR)$(TUNED_PROFILESDIR)
	mkdir -p $(DESTDIR)/var/lib/tuned
	mkdir -p $(DESTDIR)/var/log/tuned
	mkdir -p $(DESTDIR)/run/tuned
	mkdir -p $(DESTDIR)$(DOCDIR)
	mkdir -p $(DESTDIR)$(SYSCONFDIR)
	mkdir -p $(DESTDIR)$(TUNED_RECOMMEND_DIR)
	mkdir -p $(DESTDIR)$(TUNED_USER_RECOMMEND_DIR)

install: install-dirs

	# binaries
	install -Dm 0755 tuned.py $(DESTDIR)/usr/sbin/tuned
	install -Dm 0755 tuned-adm.py $(DESTDIR)/usr/sbin/tuned-adm
	install -Dm 0755 tuned-gui.py $(DESTDIR)/usr/sbin/tuned-gui
	sed -i -r -e $(SHEBANG_REWRITE_REGEX) \
		$(DESTDIR)/usr/sbin/tuned \
		$(DESTDIR)/usr/sbin/tuned-adm \
		$(DESTDIR)/usr/sbin/tuned-gui
	touch -r tuned.py $(DESTDIR)/usr/sbin/tuned
	touch -r tuned-adm.py $(DESTDIR)/usr/sbin/tuned-adm
	touch -r tuned-gui.py $(DESTDIR)/usr/sbin/tuned-gui
	$(foreach file, $(wildcard systemtap/*), \
		install -Dpm 0755 $(file) $(DESTDIR)/usr/sbin/$(notdir $(file));)
	sed -i -r -e $(SHEBANG_REWRITE_REGEX) \
		$(DESTDIR)/usr/sbin/varnetload
	touch -r systemtap/varnetload $(DESTDIR)/usr/sbin/varnetload

	# tools
	install -Dm 0755 experiments/powertop2tuned.py $(DESTDIR)/usr/bin/powertop2tuned
	sed -i -r -e $(SHEBANG_REWRITE_REGEX) \
		$(DESTDIR)/usr/bin/powertop2tuned
	touch -r experiments/powertop2tuned.py $(DESTDIR)/usr/bin/powertop2tuned

	# libexec scripts
	$(foreach file, $(wildcard libexec/*), \
		install -Dm 0755 $(file) $(DESTDIR)/usr/libexec/tuned/$(notdir $(file)); \
		sed -i -r -e $(SHEBANG_REWRITE_REGEX) \
			$(DESTDIR)/usr/libexec/tuned/$(notdir $(file)); \
		touch -r $(file) $(DESTDIR)/usr/libexec/tuned/$(notdir $(file)); \
		)

clean:
	find -name "*.pyc" | xargs rm -f
	rm -rf $(VERSIONED_NAME) rpm-build-dir

test:
	$(PYTHON) -m unittest discover tests

lint:
	$(PYLINT) -E -f parseable tuned *.py

.PHONY: clean archive srpm tag test lint
